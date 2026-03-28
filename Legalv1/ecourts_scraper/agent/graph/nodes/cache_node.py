"""
CacheNode — check and store scrape results in ecourts_cache.

check_cache(state, config) → state delta
  Sets state["cache_hit"] = True and state["result"] if found.
  Returns empty dict (no mutation) if not found.

store_cache(state, config) → state delta
  Writes state["result"] to cache using the scraper's build_cache_key / get_data_type.
  Called from cache_result step node.
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging
from datetime import datetime, timezone

logger = logging.getLogger("django")


def check_cache(state: dict, config: RunnableConfig) -> dict:
    """
    Check MongoDB ecourts_cache for a previously scraped result.
    Returns {"cache_hit": True, "result": <data>, "current_step": "check_cache"}
    on hit, or {"cache_hit": False, "current_step": "check_cache"} on miss.
    """
    from ecourts_scraper.cache.cache_manager import EcourtsCacheManager

    scraper = config["configurable"]["sideband"].get("scraper")
    params = state["params"]
    method = params.get("_method", "")

    if not scraper:
        # Scraper not yet resolved (e.g. caught before resolve_court ran); skip cache
        return {"cache_hit": False, "current_step": "check_cache"}

    try:
        cache_key = scraper.build_cache_key(method, params)
        cached = EcourtsCacheManager().get(cache_key)
        if cached:
            logger.info("[graph] cache hit key=%s", cache_key)
            return {
                "cache_hit": True,
                "result": cached.get("data"),
                "current_step": "check_cache",
            }
    except Exception as e:
        logger.warning("[graph] check_cache error: %s", e)

    return {"cache_hit": False, "current_step": "check_cache"}


def store_cache(state: dict, config: RunnableConfig) -> dict:
    """Write state['result'] into ecourts_cache."""
    from ecourts_scraper.cache.cache_manager import EcourtsCacheManager

    scraper = config["configurable"]["sideband"]["scraper"]
    params = state["params"]
    method = params.get("_method", "")

    try:
        cache_key = scraper.build_cache_key(method, params)
        data_type = scraper.get_data_type(method)
        result = state.get("result") or {}
        EcourtsCacheManager().set(
            cache_key,
            data_type,
            result,
            scraper.get_source_site(),
        )
        logger.info("[graph] cached key=%s", cache_key)
    except Exception as e:
        logger.warning("[graph] store_cache error: %s", e)

    return {"current_step": "cache_result"}
