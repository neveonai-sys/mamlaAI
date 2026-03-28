"""
ParserNode — extract and normalize results from the page.

parse(state, config) → state delta
  Calls scraper.parse_results(page, params).
  The result is validated by scraper.validate_result().
  If validation fails, sets error for error_handler.
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging

logger = logging.getLogger("django")


def parse(state: dict, config: RunnableConfig) -> dict:
    """Parse results from the current page."""
    cfg = config["configurable"]
    sb = cfg["sideband"]
    scraper = sb["scraper"]
    page = sb.get("page")
    params = state.get("params", {})

    if not page:
        return {"error": "No browser page for parsing", "current_step": "parse"}

    try:
        result = scraper.parse_results(page, params)
        logger.info("[graph] parse OK workflow=%s", state.get("workflow"))
        return {"result": result, "current_step": "parse"}
    except Exception as e:
        logger.error("[graph] parse failed: %s", e)
        return {
            "error": f"Parse failed: {e}",
            "current_step": "parse",
        }


def validate(state: dict, config: RunnableConfig) -> dict:
    """Validate the parsed result via scraper.validate_result()."""
    cfg = config["configurable"]
    scraper = cfg["sideband"]["scraper"]
    result = state.get("result")

    try:
        valid = scraper.validate_result(result) if result else False
    except Exception as e:
        logger.warning("[graph] validate error: %s", e)
        valid = False

    if not valid:
        logger.warning("[graph] validate failed job=%s", state.get("job_id"))
        return {
            "error": "Validation failed — scraper returned no usable result",
            "current_step": "validate",
        }

    return {"current_step": "validate"}


# ─── Edge router for validate outcome ────────────────────────────────────────
def route_validate(state: dict) -> str:
    """Conditional edge: valid result → cache_result, else → error_handler."""
    if state.get("error") and "Validation failed" in state.get("error", ""):
        return "error_handler"
    if state.get("result") is not None:
        return "cache_result"
    return "error_handler"
