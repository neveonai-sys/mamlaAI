"""
Management command: initialize_prod_db

Creates all MongoDB collections and indexes for a fresh database.
Idempotent — safe to run multiple times; all index creation calls check
whether the index already exists before creating it.

Usage:
    DJANGO_MODE=prod python manage.py initialize_prod_db
    DJANGO_MODE=dev  python manage.py initialize_prod_db   # works on dev DB too
"""
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import OperationFailure

from core.init_clients import get_mongo_client, get_mongo_db, ensure_indexes

logger = logging.getLogger("django")


class Command(BaseCommand):
    help = (
        "Create all MongoDB collections and indexes for a fresh database. "
        "Idempotent — safe to re-run."
    )

    def handle(self, *args, **options):
        db_name = settings.MONGO_DB_NAME
        self.stdout.write(f"Initialising MongoDB database: {db_name}")

        results = []

        # ── 1. Core app indexes (user_details, drafts, cases, etc.) ─────────
        results.append(self._run("core ensure_indexes", self._core_indexes))

        # ── 2. eCourts hierarchy (ecourt_scrapped) ───────────────────────────
        results.append(self._run("ecourt_scrapped ensure_indexes", self._ecourts_hierarchy_indexes))

        # ── 3. eCourts scraper cache (only if app is installed) ──────────────
        results.append(self._run("ecourts_scraper cache indexes", self._ecourts_scraper_indexes))

        # ── 4. AI-drafts extended indexes ────────────────────────────────────
        results.append(self._run("aidrafts extended indexes", self._aidrafts_extended_indexes))

        # ── 5. TalkDoc RAG collections ───────────────────────────────────────
        results.append(self._run("talkdoc RAG indexes", self._talkdoc_indexes))

        # ── 6. User sessions indexes ─────────────────────────────────────────
        results.append(self._run("user_sessions indexes", self._user_sessions_indexes))

        # ── 7. ecourts_scraper agent registries ─────────────────────────────
        results.append(self._run("ecourts_scraper agent registry indexes", self._agent_registry_indexes))

        # ── Summary ─────────────────────────────────────────────────────────
        ok = sum(1 for r in results if r)
        fail = len(results) - ok
        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {ok}/{len(results)} step(s) succeeded."
            + (f"  {fail} step(s) had errors (check logs above)." if fail else "")
        ))

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _run(self, label, fn):
        self.stdout.write(f"  → {label} ...", ending=" ")
        try:
            fn()
            self.stdout.write(self.style.SUCCESS("OK"))
            return True
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"FAILED: {exc}"))
            logger.exception("initialize_prod_db: %s failed", label)
            return False

    # ── Step implementations ─────────────────────────────────────────────────

    def _core_indexes(self):
        """Delegates to core.init_clients.ensure_indexes() — covers:
        user_details, draft_content_data, aidrafts_complete_data,
        cases, hearing_notes, case_notes, case_tasks.
        """
        ensure_indexes()

    def _ecourts_hierarchy_indexes(self):
        from ecourt_scrapped.services.ecourts_crawler import ensure_indexes as ecourts_ensure
        ecourts_ensure()

    def _ecourts_scraper_indexes(self):
        try:
            from ecourts_scraper.cache.collections import ensure_ecourts_indexes
            ensure_ecourts_indexes()
        except ImportError:
            self.stdout.write("  (ecourts_scraper not installed — skipped)")

    def _aidrafts_extended_indexes(self):
        db = get_mongo_db()
        collection = db["aidrafts_complete_data"]

        indexes = [
            IndexModel([("user_id", ASCENDING)], name="user_id_idx"),
            IndexModel([("user_id", ASCENDING), ("created_on", DESCENDING)], name="user_created_idx"),
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)], name="user_status_idx"),
            IndexModel([("draft_for.personal", ASCENDING)], name="personal_idx"),
            IndexModel([("draft_for.caseid", ASCENDING)], name="caseid_idx"),
            IndexModel([("draft_for.clientid", ASCENDING)], name="clientid_idx"),
            IndexModel([("draft_for.caseid_with_clientid", ASCENDING)], name="caseid_clientid_idx"),
            IndexModel([("created_on", DESCENDING)], name="created_on_idx"),
            IndexModel([("last_updated_on", DESCENDING)], name="last_updated_idx"),
            IndexModel([("status", ASCENDING), ("last_updated_on", DESCENDING)], name="status_updated_idx"),
        ]
        # Build a set of existing key patterns (as tuples) to avoid
        # "IndexOptionsConflict" when the same field already has an
        # auto-named index (e.g. "user_id_1") from an earlier migration.
        existing_by_name = {idx["name"] for idx in collection.list_indexes()}
        existing_key_patterns = {
            tuple(tuple(pair) for pair in idx["key"].items())
            for idx in collection.list_indexes()
        }
        for idx in indexes:
            if idx.document["name"] in existing_by_name:
                continue  # exact name already present
            key_pattern = tuple(tuple(pair) for pair in idx.document["key"].items())
            if key_pattern in existing_key_patterns:
                continue  # same key pattern exists under a different name — skip
            try:
                collection.create_indexes([idx])
            except OperationFailure as exc:
                if exc.code == 85:  # IndexOptionsConflict — race or edge case, safe to ignore
                    pass
                else:
                    raise

    def _talkdoc_indexes(self):
        db = get_mongo_db()

        doc_indexes = [
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created_idx"),
            IndexModel([("user_id", ASCENDING), ("status", ASCENDING)], name="user_status_idx"),
            IndexModel([("matter.personal", ASCENDING)], name="matter_personal_idx"),
            IndexModel([("matter.caseid", ASCENDING)], name="matter_caseid_idx"),
            IndexModel([("matter.clientid", ASCENDING)], name="matter_clientid_idx"),
            IndexModel([("status", ASCENDING)], name="status_idx"),
        ]
        session_indexes = [
            IndexModel(
                [("user_id", ASCENDING), ("deleted", ASCENDING), ("last_message_at", DESCENDING)],
                name="user_deleted_lastmsg_idx",
            ),
            IndexModel([("user_id", ASCENDING), ("has_docs", ASCENDING)], name="user_hasdocs_idx"),
            IndexModel([("doc_ids", ASCENDING)], name="docids_idx"),
        ]
        message_indexes = [
            IndexModel([("session_id", ASCENDING), ("created_at", ASCENDING)], name="session_created_idx"),
            IndexModel([("role", ASCENDING)], name="role_idx"),
        ]
        chunk_indexes = [
            IndexModel([("doc_id", ASCENDING)], name="docid_idx"),
            IndexModel([("session_id", ASCENDING)], name="sessionid_idx"),
        ]

        db["rag_documents"].create_indexes(doc_indexes)
        db["rag_chat_sessions"].create_indexes(session_indexes)
        db["rag_messages"].create_indexes(message_indexes)
        db["rag_chunks"].create_indexes(chunk_indexes)

    def _user_sessions_indexes(self):
        db = get_mongo_db()
        session_indexes = [
            IndexModel([("user_id", ASCENDING), ("is_active", ASCENDING)], name="user_active_idx"),
            IndexModel([("session_token", ASCENDING)], name="session_token_idx", unique=True, sparse=True),
            IndexModel([("last_activity", DESCENDING)], name="last_activity_idx"),
            IndexModel([("created_at", DESCENDING)], name="created_at_idx"),
        ]
        if "user_sessions" not in db.list_collection_names():
            db.create_collection("user_sessions")
        db["user_sessions"].create_indexes(session_indexes)

    def _agent_registry_indexes(self):
        try:
            from ecourts_scraper.agent.registry.step_metrics import ensure_indexes as sm_ensure
            from ecourts_scraper.agent.registry.navigation_registry import ensure_indexes as nr_ensure
            from ecourts_scraper.agent.registry.captcha_optimizer import ensure_indexes as co_ensure
            sm_ensure()
            nr_ensure()
            co_ensure()
        except ImportError:
            self.stdout.write("  (ecourts_scraper agent registries not installed — skipped)")
