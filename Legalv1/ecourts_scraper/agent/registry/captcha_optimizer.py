"""
Captcha strategy optimizer.

Tracks per-court, per-page captcha solve stats and re-ranks the strategy order
so slower/less reliable methods are tried last.

Collection: ecourts_captcha_strategy
Default order (cold start): capsolver → easyocr → 2captcha
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

from core.init_clients import get_mongo_client, get_mongo_db

logger = logging.getLogger("django")
COLLECTION = "ecourts_captcha_strategy"

DEFAULT_STRATEGY_ORDER = ["capsolver", "easyocr", "2captcha"]


def _col():
    return get_mongo_db()[COLLECTION]


def _key(court_type: str, page: str) -> str:
    return f"{court_type}:{page}"


def get_strategy_order(court_type: str, page: str) -> list[str]:
    """
    Return captcha method order for this court/page.
    Falls back to default if no data exists or all methods have 0 attempts.
    """
    try:
        doc = _col().find_one({"_key": _key(court_type, page)})
        if doc and doc.get("strategy_order"):
            return doc["strategy_order"]
    except Exception as e:
        logger.warning("captcha_optimizer.get_strategy_order error: %s", e)
    return DEFAULT_STRATEGY_ORDER.copy()


def record_attempt(
    court_type: str,
    page: str,
    method: str,
    success: bool,
    duration_ms: int,
) -> None:
    """Update stats for a captcha solve attempt and re-rank strategies."""
    try:
        key = _key(court_type, page)
        doc = _col().find_one({"_key": key}) or {"stats": {}}
        stats = doc.get("stats", {})

        # Update this method's running stats
        m = stats.get(method, {"attempts": 0, "successes": 0, "total_ms": 0})
        m["attempts"] += 1
        if success:
            m["successes"] += 1
        m["total_ms"] = m.get("total_ms", 0) + duration_ms
        stats[method] = m

        # Re-rank: score = success_rate / avg_time (higher = better)
        # Methods with 0 attempts get score 0 and fall to end
        def _score(method_name: str) -> float:
            s = stats.get(method_name, {})
            attempts = s.get("attempts", 0)
            if attempts == 0:
                return 0.0
            success_rate = s.get("successes", 0) / attempts
            avg_ms = max(s.get("total_ms", 1) / attempts, 1)
            return success_rate / avg_ms * 10000  # scale up for readability

        ordered = sorted(
            DEFAULT_STRATEGY_ORDER,
            key=lambda m: _score(m),
            reverse=True,
        )

        _col().update_one(
            {"_key": key},
            {
                "$set": {
                    "_key": key,
                    "court_type": court_type,
                    "page": page,
                    "stats": stats,
                    "strategy_order": ordered,
                    "last_optimized": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )
    except Exception as e:
        logger.warning("captcha_optimizer.record_attempt error: %s", e)


def ensure_indexes() -> None:
    col = _col()
    existing = col.index_information()
    if "_key_1" not in existing:
        col.create_index([("_key", 1)], unique=True)
