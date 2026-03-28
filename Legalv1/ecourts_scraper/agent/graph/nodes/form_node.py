"""
FormNode — fill search/lookup form fields.

fill_form(state, config) → state delta
  Delegates to scraper.fill_form(page, params).
  The scraper knows which fields to fill for its specific court form.
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging

logger = logging.getLogger("django")


def fill_form(state: dict, config: RunnableConfig) -> dict:
    """Fill all form fields for the current search."""
    cfg = config["configurable"]
    sb = cfg["sideband"]
    scraper = sb["scraper"]
    page = sb.get("page")
    params = state.get("params", {})

    if not page:
        return {"error": "No browser page for form filling", "current_step": "fill_form"}

    try:
        scraper.fill_form(page, params)
        logger.info("[graph] fill_form OK workflow=%s", state.get("workflow"))
        return {"current_step": "fill_form"}
    except Exception as e:
        logger.error("[graph] fill_form failed: %s", e)
        return {
            "error": f"Form fill failed: {e}",
            "current_step": "fill_form",
        }
