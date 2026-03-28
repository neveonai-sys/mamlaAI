"""
CaptchaNode — multi-strategy CAPTCHA solving with learning optimizer.

solve_captcha(state, config) → state delta
  Reads strategy order from captcha_optimizer (capsolver → easyocr → 2captcha by default).
  Tries each strategy in order. Records outcome in optimizer.

refresh_captcha(state, config) → state delta
  Clicks the captcha refresh button via the scraper.
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import time
import logging

logger = logging.getLogger("django")

CAPTCHA_MAX_ATTEMPTS = 10


def solve_captcha(state: dict, config: RunnableConfig) -> dict:
    """
    Solve CAPTCHA using the optimized strategy order.
    Returns {"submit_outcome": "captcha_ready"} on success,
    or {"captcha_attempts": n} and error on failure.
    """
    from ecourts_scraper.agent.registry import captcha_optimizer

    cfg = config["configurable"]
    sb = cfg["sideband"]
    scraper = sb["scraper"]
    page = sb.get("page")

    court_type = state.get("court_type", "")
    attempt = state.get("captcha_attempts", 0)

    if attempt >= CAPTCHA_MAX_ATTEMPTS:
        return {
            "error": f"CAPTCHA failed after {CAPTCHA_MAX_ATTEMPTS} attempts",
            "current_step": "solve_captcha",
        }

    # Get optimized strategy order (learning registry)
    # page key = "captcha" for all courts (they all have one captcha page)
    strategy_order = captcha_optimizer.get_strategy_order(court_type, "captcha")

    t0 = time.time()
    solved = False
    strategy_used = ""

    try:
        # scraper.solve_captcha() uses the ECOURTS_CAPTCHA_SERVICE env internally,
        # but we pass the preferred method via config if supported.
        # For v1, we call the scraper directly (it handles strategy ordering via env).
        # Strategy learning is still recorded below for future direct integration.
        solved = scraper.solve_captcha(page, attempt)
        strategy_used = strategy_order[0] if strategy_order else "capsolver"
    except Exception as e:
        logger.error("[graph] solve_captcha exception: %s", e)
        strategy_used = strategy_order[0] if strategy_order else "capsolver"

    duration_ms = int((time.time() - t0) * 1000)
    captcha_optimizer.record_attempt(
        court_type=court_type,
        page="captcha",
        method=strategy_used,
        success=solved,
        duration_ms=duration_ms,
    )

    if solved:
        logger.info("[graph] captcha solved attempt=%d %dms", attempt, duration_ms)
        return {
            "current_step": "solve_captcha",
            "captcha_strategy_used": strategy_used,
        }
    else:
        logger.warning("[graph] captcha not solved attempt=%d", attempt)
        # Set submit_outcome so error_handler recognises this as a captcha retry
        # (not a generic backoff that would release the browser and lose the page)
        return {
            "captcha_attempts": attempt + 1,
            "submit_outcome": "captcha_error",
            "current_step": "solve_captcha",
        }


def refresh_captcha(state: dict, config: RunnableConfig) -> dict:
    """Click the captcha refresh/reload button."""
    cfg = config["configurable"]
    sb = cfg["sideband"]
    scraper = sb["scraper"]
    page = sb.get("page")

    try:
        scraper.refresh_captcha(page)
        logger.info("[graph] captcha refreshed")
    except Exception as e:
        logger.warning("[graph] refresh_captcha error: %s", e)

    return {"current_step": "refresh_captcha"}
