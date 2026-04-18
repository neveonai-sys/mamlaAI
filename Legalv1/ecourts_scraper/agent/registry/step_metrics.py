"""
Workflow step metrics tracker.

Records full workflow run timings into ecourts_workflow_metrics.
Used by the finalize node after each completed/failed scrape to build
the performance dataset for the learning registry.

Collection: ecourts_workflow_metrics
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

from core.init_clients import get_mongo_client, get_mongo_db

logger = logging.getLogger("django")
COLLECTION = "ecourts_workflow_metrics"


def _col():
    return get_mongo_db()[COLLECTION]


def record_run(
    job_id: str,
    search_type: str,
    court_type: str,
    workflow: str,
    outcome: str,           # completed | failed
    step_log: list[dict],
    started_at: datetime | None = None,
) -> None:
    """
    Persist a completed workflow run with per-step timing.
    Called once per job after finalize.
    """
    try:
        now = datetime.now(timezone.utc)
        started = started_at or now

        # total_duration_ms from step_log sum
        total_ms = sum(s.get("duration_ms", 0) for s in step_log)

        _col().insert_one(
            {
                "job_id": job_id,
                "search_type": search_type,
                "court_type": court_type,
                "workflow": workflow,
                "outcome": outcome,
                "steps": step_log,
                "total_duration_ms": total_ms,
                "started_at": started,
                "completed_at": now,
            }
        )
    except Exception as e:
        logger.warning("step_metrics.record_run error: %s", e)


def ensure_indexes() -> None:
    col = _col()
    existing = col.index_information()
    if "completed_at_-1" not in existing:
        col.create_index([("completed_at", -1)])
    if "search_type_1_outcome_1" not in existing:
        col.create_index([("search_type", 1), ("outcome", 1)])
    if "job_id_1" not in existing:
        col.create_index([("job_id", 1)])
