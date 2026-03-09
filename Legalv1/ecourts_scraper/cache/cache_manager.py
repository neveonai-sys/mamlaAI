"""
Cache manager for eCourts scraped data.
Handles get/set/invalidate with TTL-based expiry in MongoDB.
"""
import logging
from datetime import datetime, timedelta, timezone
from ecourts_scraper.cache.collections import get_cache_collection
from ecourts_scraper.constants import CACHE_TTL

logger = logging.getLogger("django")


class EcourtsCacheManager:

    def __init__(self):
        self._col = get_cache_collection()

    def get(self, cache_key: str) -> dict | None:
        """
        Retrieve cached data by key.
        Returns the full document (including metadata) or None if expired/missing.
        """
        doc = self._col.find_one(
            {"cache_key": cache_key},
            {"_id": 0},
        )
        if not doc:
            return None

        expires_at = doc.get("expires_at")
        if expires_at:
            now = datetime.now(timezone.utc)
            if getattr(expires_at, "tzinfo", None) is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < now:
                return None

        return doc

    def set(self, cache_key: str, data_type: str, data: dict, source_site: str = ""):
        """Store scraped data with appropriate TTL."""
        ttl_hours = CACHE_TTL.get(data_type, 24)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=ttl_hours)

        doc = {
            "cache_key": cache_key,
            "data_type": data_type,
            "data": data,
            "source_site": source_site,
            "scraped_at": now,
            "expires_at": expires_at,
            "scrape_status": "success",
        }
        self._col.update_one(
            {"cache_key": cache_key},
            {"$set": doc},
            upsert=True,
        )
        logger.debug("Cached %s -> %s (TTL %sh)", data_type, cache_key, ttl_hours)

    def invalidate(self, cache_key: str):
        """Remove a specific cache entry."""
        self._col.delete_one({"cache_key": cache_key})

    def invalidate_by_type(self, data_type: str):
        """Remove all cache entries of a given type."""
        result = self._col.delete_many({"data_type": data_type})
        logger.info("Invalidated %d entries of type %s", result.deleted_count, data_type)

    def get_keys_by_prefix(self, prefix: str) -> list[str]:
        """Return all cache keys matching a prefix (non-expired)."""
        now = datetime.now(timezone.utc)
        cursor = self._col.find(
            {
                "cache_key": {"$regex": f"^{prefix}"},
                "$or": [
                    {"expires_at": {"$gt": now}},
                    {"expires_at": {"$exists": False}},
                ],
            },
            {"cache_key": 1, "_id": 0},
        )
        return [doc["cache_key"] for doc in cursor]

    def cleanup_expired(self) -> int:
        """Manually remove expired entries (TTL index also handles this)."""
        result = self._col.delete_many(
            {"expires_at": {"$lt": datetime.now(timezone.utc)}}
        )
        return result.deleted_count
