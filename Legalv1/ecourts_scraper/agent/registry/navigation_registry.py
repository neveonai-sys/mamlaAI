"""
Navigation anchor registry.

Stores proven selector + timing data per (court_type, workflow, step_name).
Used by navigator_node to skip re-discovery on repeat scrapes of unchanged pages.

Collection: ecourts_navigation_registry
"""
from __future__ import annotations
import hashlib
import logging
from datetime import datetime, timezone

from core.init_clients import get_mongo_client

logger = logging.getLogger("django")
COLLECTION = "ecourts_navigation_registry"


def _col():
    return get_mongo_client()["legaldb"][COLLECTION]


def _key(court_type: str, workflow: str, step_name: str) -> str:
    return f"{court_type}:{workflow}:{step_name}"


def page_fingerprint(html_snippet: str) -> str:
    """Stable 8-char hash of a page section for change detection."""
    return hashlib.sha256(html_snippet.encode()).hexdigest()[:8]


def get_best_selectors(
    court_type: str, workflow: str, step_name: str
) -> dict | None:
    """
    Return the best known selector for this step, or None if no anchor exists
    or if the anchor has too high a failure rate (>50% with >10 attempts).
    """
    try:
        doc = _col().find_one({"_key": _key(court_type, workflow, step_name)})
        if not doc:
            return None
        total = doc.get("success_count", 0) + doc.get("fail_count", 0)
        if total >= 10 and doc.get("fail_count", 0) / total > 0.5:
            return None  # too unreliable, fall back to constants
        return {
            "selector": doc.get("selector"),
            "page_fingerprint": doc.get("page_fingerprint"),
            "avg_duration_ms": doc.get("avg_duration_ms", 0),
        }
    except Exception as e:
        logger.warning("navigation_registry.get_best_selectors error: %s", e)
        return None


def record_step(
    court_type: str,
    workflow: str,
    step_name: str,
    selector: dict,
    duration_ms: int,
    success: bool,
    page_fp: str = "",
    fail_reason: str = "",
) -> None:
    """Upsert a step result into the registry."""
    try:
        key = _key(court_type, workflow, step_name)
        now = datetime.now(timezone.utc)

        # Pull current for running avg calculation
        existing = _col().find_one({"_key": key}) or {}
        prev_avg = existing.get("avg_duration_ms", duration_ms)
        prev_count = existing.get("success_count", 0) + existing.get("fail_count", 0)
        new_avg = int((prev_avg * prev_count + duration_ms) / (prev_count + 1))

        update: dict = {
            "$set": {
                "_key": key,
                "court_type": court_type,
                "workflow": workflow,
                "step_name": step_name,
                "selector": selector,
                "avg_duration_ms": new_avg,
                "updated_at": now,
            },
            "$inc": {
                "success_count" if success else "fail_count": 1,
            },
        }
        if success:
            update["$set"]["last_success"] = now
            if page_fp:
                update["$set"]["page_fingerprint"] = page_fp
        else:
            update["$set"]["last_fail_reason"] = fail_reason

        _col().update_one({"_key": key}, update, upsert=True)
    except Exception as e:
        logger.warning("navigation_registry.record_step error: %s", e)


def ensure_indexes() -> None:
    col = _col()
    existing = col.index_information()
    if "_key_1" not in existing:
        col.create_index([("_key", 1)], unique=True)
    if "court_type_1_workflow_1" not in existing:
        col.create_index([("court_type", 1), ("workflow", 1)])
