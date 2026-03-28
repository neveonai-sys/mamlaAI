"""
SubmitNode — submit form and classify the outcome.

submit(state, config) → state delta
  Calls scraper.submit_and_check(page) which returns one of:
    "success"       → proceed to parse
    "captcha_error" → retry captcha
    "blocked"       → rotate proxy
    "not_found"     → result is empty, end gracefully
    "error"         → generic error, backoff

The outcome is stored in state["submit_outcome"] for the edge router.
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging

logger = logging.getLogger("django")


def submit(state: dict, config: RunnableConfig) -> dict:
    """Submit the form and return the outcome classification."""
    cfg = config["configurable"]
    sb = cfg["sideband"]
    scraper = sb["scraper"]
    page = sb.get("page")

    if not page:
        return {
            "submit_outcome": "error",
            "error": "No browser page for form submission",
            "current_step": "submit",
        }

    try:
        outcome = scraper.submit_and_check(page)
        logger.info("[graph] submit outcome=%s job=%s", outcome, state.get("job_id"))
        delta: dict = {"submit_outcome": outcome, "current_step": "submit"}

        if outcome == "not_found":
            delta["result"] = {"status": "not_found", "message": "No records found."}

        return delta
    except Exception as e:
        logger.error("[graph] submit failed: %s", e)
        return {
            "submit_outcome": "error",
            "error": f"Submit failed: {e}",
            "current_step": "submit",
        }


# ─── Edge router for submit outcome ─────────────────────────────────────────
def route_submit_outcome(state: dict) -> str:
    """Conditional edge: maps submit_outcome → next node name."""
    outcome = state.get("submit_outcome", "error")
    return {
        "success": "parse",
        "captcha_error": "error_handler",
        "blocked": "error_handler",
        "not_found": "__end__",
        "error": "error_handler",
    }.get(outcome, "error_handler")
