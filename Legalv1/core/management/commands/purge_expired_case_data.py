"""
Management command: purge_expired_case_data

Anonymises case-related content for users whose account deletion happened
more than the retention window ago (default 2555 days / 7 years), per the
Privacy Policy's Data Retention table: "Case documents — 7 years after
account deletion — Record-keeping obligations under the Limitation Act,
1963 and applicable Bar Council of India / professional-conduct rules."

This intentionally ANONYMISES rather than hard-deletes (Policy Section 6.3:
data retained under a legal obligation "will be anonymized rather than
deleted"), preserving the record shell for professional-conduct audit
continuity while stripping client-identifying content.

This cannot be a MongoDB TTL index: the 7-year clock starts at a *different*
document's field (user_details.deleted_at), not at case-creation time, and
the overwhelming majority of accounts are active and must never be touched.

Usage:
    python manage.py purge_expired_case_data              # dry-run, shows count
    python manage.py purge_expired_case_data --execute     # actually anonymises
    python manage.py purge_expired_case_data --days 1825   # 5-year window
"""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from core.init_clients import get_mongo_db
from core.audit_log import ACTION_CASE_DATA_PURGED, write_audit_log

_ANONYMISED_BRIEF = "[anonymised — retention period expired]"
_ANONYMISED_NAME = "Anonymised Client"


class Command(BaseCommand):
    help = "Anonymise case documents for accounts deleted more than the retention window ago (default 2555 days / 7 years)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=2555,
            help="Retention window in days after account deletion (default: 2555 / 7 years).",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            default=False,
            help="Actually anonymise records. Omitting this flag runs a dry-run.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        execute = options["execute"]
        cutoff = datetime.utcnow() - timedelta(days=days)

        db = get_mongo_db()

        expired_users = list(db["user_details"].find(
            {"deleted_at": {"$lte": cutoff}},
            {"_id": 0, "user_id": 1, "deleted_at": 1},
        ))

        if not expired_users:
            self.stdout.write(self.style.SUCCESS("No accounts have crossed the case-data retention window."))
            return

        if not execute:
            self.stdout.write(self.style.WARNING(
                f"[DRY RUN] {len(expired_users)} account(s) deleted before {cutoff.date()} "
                f"would have their case data anonymised. Run with --execute to confirm."
            ))
            for u in expired_users:
                case_count = db["cases"].count_documents({"lawyer_id": u["user_id"]})
                self.stdout.write(f"    user_id={u['user_id']} deleted_at={u['deleted_at']} cases={case_count}")
            return

        total_users = 0
        for u in expired_users:
            user_id = u["user_id"]
            case_ids = [c["_id"] for c in db["cases"].find({"lawyer_id": user_id}, {"_id": 1})]

            cases_result = db["cases"].update_many(
                {"lawyer_id": user_id},
                {"$set": {
                    "brief": _ANONYMISED_BRIEF,
                    "client_name_display": _ANONYMISED_NAME,
                    "case_data_purged_at": datetime.utcnow(),
                }},
            )

            notes_result = db["case_notes"].update_many(
                {"case_id": {"$in": case_ids}},
                {"$set": {"content": _ANONYMISED_BRIEF}},
            ) if case_ids else None

            hearing_result = db["hearing_notes"].update_many(
                {"case_id": {"$in": case_ids}},
                {"$set": {"content": _ANONYMISED_BRIEF, "outcome": _ANONYMISED_BRIEF}},
            ) if case_ids else None

            drafts_result = db["aidrafts_complete_data"].update_many(
                {"user_id": user_id},
                {"$set": {"draft_sections": [], "original_draft": []}},
            )

            conversations_result = db["draft_conversations"].update_many(
                {"user_id": user_id},
                {"$set": {"messages": []}},
            )

            write_audit_log(
                ACTION_CASE_DATA_PURGED,
                actor_id="system",
                target_id=user_id,
                metadata={
                    "cases_anonymised": cases_result.modified_count,
                    "case_notes_anonymised": notes_result.modified_count if notes_result else 0,
                    "hearing_notes_anonymised": hearing_result.modified_count if hearing_result else 0,
                    "ai_drafts_anonymised": drafts_result.modified_count,
                    "draft_conversations_anonymised": conversations_result.modified_count,
                    "retention_days": days,
                },
            )
            total_users += 1

        self.stdout.write(self.style.SUCCESS(
            f"Anonymised case data for {total_users} account(s) deleted before {cutoff.date()}."
        ))
