"""
MongoDB collection definitions and index management for eCourts scraper.
"""
import logging
from datetime import datetime, timedelta
from django.conf import settings
from core.init_clients import get_mongo_client, get_mongo_db

logger = logging.getLogger("django")

COLLECTION_ECOURTS_CACHE = "ecourts_cache"
COLLECTION_SCRAPE_JOBS = "ecourts_scrape_jobs"
COLLECTION_SELECTORS = "ecourts_selectors"
COLLECTION_REFERENCE_DATA = "ecourts_reference_data"


def get_db():
    return get_mongo_db()


def get_cache_collection():
    return get_db()[COLLECTION_ECOURTS_CACHE]


def get_jobs_collection():
    return get_db()[COLLECTION_SCRAPE_JOBS]


def get_selectors_collection():
    return get_db()[COLLECTION_SELECTORS]


def get_reference_collection():
    return get_db()[COLLECTION_REFERENCE_DATA]


def ensure_ecourts_indexes():
    """Create necessary indexes for eCourts collections."""
    try:
        db = get_db()

        cache_col = db[COLLECTION_ECOURTS_CACHE]
        existing = cache_col.index_information()
        if "cache_key_1" not in existing:
            cache_col.create_index([("cache_key", 1)], unique=True)
        if "expires_at_1" not in existing:
            cache_col.create_index(
                [("expires_at", 1)], expireAfterSeconds=0
            )
        if "data_type_1_scraped_at_-1" not in existing:
            cache_col.create_index([("data_type", 1), ("scraped_at", -1)])

        jobs_col = db[COLLECTION_SCRAPE_JOBS]
        existing = jobs_col.index_information()
        if "user_id_1_created_at_-1" not in existing:
            jobs_col.create_index([("user_id", 1), ("created_at", -1)])
        if "status_1" not in existing:
            jobs_col.create_index([("status", 1)])

        sel_col = db[COLLECTION_SELECTORS]
        existing = sel_col.index_information()
        if "site_1_page_1_element_1" not in existing:
            sel_col.create_index(
                [("site", 1), ("page", 1), ("element", 1)], unique=True
            )

        ref_col = db[COLLECTION_REFERENCE_DATA]
        existing = ref_col.index_information()
        if "reference_key_1" not in existing:
            ref_col.create_index([("reference_key", 1)], unique=True)
        if "scope_1_refreshed_at_-1" not in existing:
            ref_col.create_index([("scope", 1), ("refreshed_at", -1)])

        logger.info("eCourts indexes created/verified")
    except Exception as e:
        logger.error("Failed to create eCourts indexes: %s", e)
