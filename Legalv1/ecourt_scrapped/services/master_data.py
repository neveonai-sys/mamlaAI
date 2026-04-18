"""
MongoDB-backed master data for eCourts dropdowns.

Two data sources (tried in order):
  1. Pre-crawled per-entity collections (ecourts_states, ecourts_districts, …)
     — populated by `manage.py seed_ecourts_hierarchy` or the /seed/ endpoint.
  2. Live scrape from eCourts + cache in ecourts_master_data collection
     — on-demand when pre-crawled data doesn't exist; uses curl_cffi (no FastAPI).
"""

import logging
from datetime import datetime, timedelta

from core.init_clients import get_mongo_client, get_mongo_db

logger = logging.getLogger("django")

TTL_MONTHLY = timedelta(days=30)
TTL_WEEKLY = timedelta(days=7)

# Maps kind → TTL for caching
_TTL_MAP = {
    "states":              TTL_MONTHLY,
    "districts":           TTL_MONTHLY,
    "complexes":           TTL_WEEKLY,
    "establishments":      TTL_WEEKLY,
    "courts":              TTL_WEEKLY,
    "police_stations":     TTL_WEEKLY,
    "order_case_types":    TTL_WEEKLY,
    "order_court_numbers": TTL_WEEKLY,
}


def _db():
    return get_mongo_db()


def _cache_collection():
    return _db()["ecourts_master_data"]


def _build_key(kind: str, params: dict) -> str:
    if not params:
        return kind
    parts = ":".join(f"{k}={v}" for k, v in sorted(params.items()) if v)
    return f"{kind}:{parts}"


# ─── Pre-crawled collection readers (fast, no network) ────────────────────────

def _read_from_crawled(kind: str, params: dict) -> list | None:
    """
    Try reading from the pre-crawled per-entity collections.
    Returns list of items or None if data doesn't exist.
    """
    db = _db()

    if kind == "states":
        docs = list(db.ecourts_states.find({}, {"_id": 0, "updated_at": 0}).sort("name", 1))
        return docs if docs else None

    if kind == "districts":
        docs = list(db.ecourts_districts.find(
            {"state_code": params.get("state_code")},
            {"_id": 0, "updated_at": 0}
        ).sort("name", 1))
        return docs if docs else None

    if kind == "complexes":
        docs = list(db.ecourts_complexes.find(
            {"state_code": params.get("state_code"),
             "dist_code": params.get("dist_code")},
            {"_id": 0, "updated_at": 0}
        ).sort("name", 1))
        return docs if docs else None

    if kind == "establishments":
        cc = params.get("court_complex_code", "")
        docs = list(db.ecourts_establishments.find(
            {"state_code": params.get("state_code"),
             "dist_code": params.get("dist_code"),
             "$or": [{"complex_code": cc}, {"bare_complex": cc}]},
            {"_id": 0, "updated_at": 0}
        ).sort("name", 1))
        return docs if docs else None

    if kind == "courts":
        cc = params.get("court_complex_code", "")
        docs = list(db.ecourts_courts.find(
            {"state_code": params.get("state_code"),
             "dist_code": params.get("dist_code"),
             "$or": [{"complex_code": cc}, {"bare_complex": cc}],
             "est_code": params.get("est_code")},
            {"_id": 0, "updated_at": 0}
        ).sort("name", 1))
        return docs if docs else None

    if kind == "police_stations":
        cc = params.get("court_complex_code", "")
        docs = list(db.ecourts_police_stations.find(
            {"state_code": params.get("state_code"),
             "dist_code": params.get("dist_code"),
             "$or": [{"complex_code": cc}, {"bare_complex": cc}],
             "est_code": params.get("est_code")},
            {"_id": 0, "updated_at": 0}
        ).sort("name", 1))
        return docs if docs else None

    if kind == "order_case_types":
        cc = params.get("court_complex_code", "")
        docs = list(db.ecourts_case_types.find(
            {"state_code": params.get("state_code"),
             "dist_code": params.get("dist_code"),
             "$or": [{"complex_code": cc}, {"bare_complex": cc}],
             "est_code": params.get("est_code")},
            {"_id": 0, "updated_at": 0}
        ).sort("name", 1))
        return docs if docs else None

    return None


# ─── Live scrape from eCourts + cache (no FastAPI dependency) ─────────────────

def _scrape_live(kind: str, params: dict) -> list:
    """
    Scrape dropdown data directly from eCourts using curl_cffi.
    Returns list of {code, name, ...} items.
    """
    from ecourt_scrapped.services.ecourts_crawler import (
        STATES, bare_complex,
        scrape_districts, scrape_complexes, scrape_establishments,
        scrape_courts, scrape_police_stations, scrape_case_types,
    )

    state_code = params.get("state_code", "")
    dist_code = params.get("dist_code", "")
    cc = params.get("court_complex_code", "")
    est_code = params.get("est_code", "")
    cc_bare = bare_complex(cc)

    if kind == "states":
        return [{"code": s["code"], "name": s["name"]} for s in STATES]
    elif kind == "districts":
        return scrape_districts(state_code)
    elif kind == "complexes":
        return scrape_complexes(state_code, dist_code)
    elif kind == "establishments":
        return scrape_establishments(state_code, dist_code, cc_bare)
    elif kind == "courts":
        return scrape_courts(state_code, dist_code, cc_bare, est_code)
    elif kind == "police_stations":
        return scrape_police_stations(state_code, dist_code, cc_bare, est_code)
    elif kind == "order_case_types":
        return scrape_case_types(state_code, dist_code, cc_bare, est_code)
    elif kind == "order_court_numbers":
        return scrape_courts(state_code, dist_code, cc_bare, est_code)
    else:
        raise ValueError(f"Unknown master data kind: {kind}")


def _scrape_and_cache(kind: str, params: dict) -> list:
    """
    Scrape from eCourts, cache in ecourts_master_data with TTL, return items.
    If eCourts is unreachable and stale cache exists, returns stale data.
    """
    ttl = _TTL_MAP.get(kind, TTL_WEEKLY)
    cache_key = _build_key(kind, params)
    col = _cache_collection()

    # Return cached if still valid
    doc = col.find_one({"_id": cache_key})
    if doc and doc.get("expires_at") and doc["expires_at"] > datetime.utcnow():
        return doc["items"]

    # Scrape live from eCourts
    try:
        items = _scrape_live(kind, params)
    except Exception:
        if doc and doc.get("items"):
            logger.warning(f"eCourts unreachable for {cache_key}, returning stale data")
            return doc["items"]
        raise

    if not isinstance(items, list):
        items = [items] if items else []

    now = datetime.utcnow()
    col.replace_one(
        {"_id": cache_key},
        {
            "_id": cache_key,
            "kind": kind,
            "params": params,
            "items": items,
            "fetched_at": now,
            "expires_at": now + ttl,
            "version": 1,
        },
        upsert=True,
    )
    return items


def get_master_data(kind: str, params: dict) -> list:
    """
    Primary entry point. Tries pre-crawled collections first,
    falls back to live scrape + cache.
    """
    crawled = _read_from_crawled(kind, params)
    if crawled is not None:
        return crawled
    return _scrape_and_cache(kind, params)


def invalidate(kind: str, params: dict):
    cache_key = _build_key(kind, params)
    _cache_collection().update_one(
        {"_id": cache_key},
        {"$set": {"expires_at": datetime.utcnow()}},
    )


# ─── Convenience functions ────────────────────────────────────────────────────

def get_states() -> list:
    return get_master_data("states", {})


def get_districts(state_code: str) -> list:
    return get_master_data("districts", {"state_code": state_code})


def get_complexes(state_code: str, dist_code: str) -> list:
    return get_master_data("complexes", {
        "state_code": state_code,
        "dist_code": dist_code,
    })


def get_establishments(state_code: str, dist_code: str,
                       court_complex_code: str) -> list:
    return get_master_data("establishments", {
        "state_code": state_code,
        "dist_code": dist_code,
        "court_complex_code": court_complex_code,
    })


def get_courts(state_code: str, dist_code: str,
               court_complex_code: str, est_code: str) -> list:
    return get_master_data("courts", {
        "state_code": state_code,
        "dist_code": dist_code,
        "court_complex_code": court_complex_code,
        "est_code": est_code,
    })


def get_police_stations(state_code: str, dist_code: str,
                        court_complex_code: str, est_code: str) -> list:
    return get_master_data("police_stations", {
        "state_code": state_code,
        "dist_code": dist_code,
        "court_complex_code": court_complex_code,
        "est_code": est_code,
    })


def get_order_case_types(state_code: str, dist_code: str,
                         court_complex_code: str, est_code: str) -> list:
    return get_master_data("order_case_types", {
        "state_code": state_code,
        "dist_code": dist_code,
        "court_complex_code": court_complex_code,
        "est_code": est_code,
    })


def get_order_court_numbers(state_code: str, dist_code: str,
                            court_complex_code: str, est_code: str) -> list:
    return get_master_data("order_court_numbers", {
        "state_code": state_code,
        "dist_code": dist_code,
        "court_complex_code": court_complex_code,
        "est_code": est_code,
    })


def refresh_expired():
    """
    Refresh all master data documents that are expired or expiring
    within 24 hours. Only refreshes existing keys.
    """
    threshold = datetime.utcnow() + timedelta(hours=24)
    col = _cache_collection()
    docs = col.find({"expires_at": {"$lte": threshold}})
    refreshed = 0
    errors = 0

    for doc in docs:
        kind = doc["kind"]
        params = doc.get("params", {})
        try:
            get_master_data(kind, params)
            refreshed += 1
        except Exception as e:
            errors += 1
            logger.error(f"[master_data refresh] {doc['_id']} FAILED: {e}")

    logger.info(f"[master_data refresh] done: {refreshed} refreshed, {errors} errors")
    return {"refreshed": refreshed, "errors": errors}
