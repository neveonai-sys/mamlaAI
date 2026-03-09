"""
Scrape job lifecycle manager.
Creates, updates, and queries jobs stored in ecourts_scrape_jobs.
"""
import uuid
import logging
from datetime import datetime, timezone
from ecourts_scraper.cache.collections import get_jobs_collection

logger = logging.getLogger("django")


class JobManager:

    def __init__(self):
        self._col = get_jobs_collection()

    def create_job(
        self,
        user_id: str,
        job_type: str,
        params: dict | None = None,
    ) -> str:
        """Create a new scrape job. Returns the job_id."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        doc = {
            "_id": job_id,
            "user_id": user_id,
            "type": job_type,
            "status": "queued",
            "progress": "queued",
            "params": params or {},
            "result": None,
            "error": None,
            "agent_state": None,
            "retry_count": 0,
            "proxy_used": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }
        self._col.insert_one(doc)
        logger.info("Created job %s type=%s user=%s", job_id, job_type, user_id)
        return job_id

    def update_progress(self, job_id: str, status: str, progress: str, **extra):
        """Update job status and progress."""
        update = {
            "status": status,
            "progress": progress,
            "updated_at": datetime.now(timezone.utc),
        }
        update.update(extra)
        self._col.update_one({"_id": job_id}, {"$set": update})

    def complete_job(self, job_id: str, result: dict):
        """Mark job as completed with result data."""
        now = datetime.now(timezone.utc)
        self._col.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "completed",
                    "progress": "done",
                    "result": result,
                    "updated_at": now,
                    "completed_at": now,
                }
            },
        )

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed."""
        now = datetime.now(timezone.utc)
        self._col.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "failed",
                    "progress": "failed",
                    "error": error,
                    "updated_at": now,
                    "completed_at": now,
                }
            },
        )

    def increment_retry(self, job_id: str) -> int:
        """Increment retry count and return new value."""
        result = self._col.find_one_and_update(
            {"_id": job_id},
            {
                "$inc": {"retry_count": 1},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=True,
        )
        return result["retry_count"] if result else 0

    def get_job(self, job_id: str) -> dict | None:
        """Get job by ID."""
        doc = self._col.find_one({"_id": job_id})
        if doc:
            doc["job_id"] = doc.pop("_id")
        return doc

    def get_user_jobs(
        self, user_id: str, limit: int = 20, status: str | None = None
    ) -> list[dict]:
        """Get recent jobs for a user."""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        cursor = (
            self._col.find(query, {"_id": 1, "type": 1, "status": 1, "progress": 1, "created_at": 1})
            .sort("created_at", -1)
            .limit(limit)
        )
        jobs = []
        for doc in cursor:
            doc["job_id"] = doc.pop("_id")
            jobs.append(doc)
        return jobs
