"""
BrowserNode — acquire and release Playwright browser contexts.

acquire_browser(state, config) → state delta
  Grabs a BrowserContext from the pool and a new Page, stores them in
  config["configurable"]["browser_ctx"] and config["configurable"]["page"]
  (non-serializable sideband — never put these in state).

release_browser(state, config) → state delta
  Releases the context back to the pool. Called in finally/finalize.
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging

logger = logging.getLogger("django")


def acquire_browser(state: dict, config: RunnableConfig) -> dict:
    """
    Acquire a browser context + open a page. Stored in config sideband.
    Respects rate_limiter if provided in configurable.
    """
    from ecourts_scraper.infra.browser_pool import browser_pool

    cfg = config["configurable"]
    rate_limiter = cfg.get("rate_limiter")

    # Rate-limit check before acquiring browser slot
    if rate_limiter and not rate_limiter.acquire(timeout=60):
        return {
            "error": "Rate limit timeout — too many requests to court site",
            "current_step": "acquire_browser",
        }

    proxy = cfg.get("proxy")
    try:
        context = browser_pool.acquire_context(proxy=proxy)
        page = browser_pool.new_page(context)
        sb = cfg["sideband"]
        sb["browser_ctx"] = context
        sb["page"] = page
        logger.info("[graph] browser acquired job=%s", state.get("job_id"))
    except Exception as e:
        logger.error("[graph] acquire_browser failed: %s", e)
        return {
            "error": f"Browser acquisition failed: {e}",
            "current_step": "acquire_browser",
        }

    return {"current_step": "acquire_browser"}


def release_browser(state: dict, config: RunnableConfig) -> dict:
    """Release browser context back to pool. Safe to call even if not acquired."""
    from ecourts_scraper.infra.browser_pool import browser_pool

    cfg = config.get("configurable", {})
    sb = cfg.get("sideband", {})
    context = sb.get("browser_ctx")
    if context:
        try:
            browser_pool.release_context(context)
            sb["browser_ctx"] = None
            sb["page"] = None
            logger.info("[graph] browser released job=%s", state.get("job_id"))
        except Exception as e:
            logger.warning("[graph] release_browser error: %s", e)

    return {"current_step": "release_browser"}
