"""
NavigatorNode — navigate to the correct court page.

navigate(state, config) → state delta
  1. Checks navigation_registry for a proven anchor selector for (court_type, workflow, "navigate").
  2. Calls scraper.navigate(page, params).
  3. Records timing and outcome in registry.

Delegates actual navigation to the scraper class (HighCourtScraper, DistrictCourtScraper,
CauseListScraper) — those classes own the URL and DOM interaction details.
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import time
import logging

logger = logging.getLogger("django")


def navigate(state: dict, config: RunnableConfig) -> dict:
    """Navigate to the court page using the scraper's navigate() method."""
    from ecourts_scraper.agent.registry import navigation_registry

    cfg = config["configurable"]
    sb = cfg["sideband"]
    scraper = sb["scraper"]
    page = sb.get("page")

    if not page:
        return {
            "error": "No browser page available for navigation",
            "current_step": "navigate",
        }

    court_type = state.get("court_type", "")
    workflow = state.get("workflow", "")
    params = state.get("params", {})

    # Check anchor registry first (learning)
    anchor = navigation_registry.get_best_selectors(court_type, workflow, "navigate")
    anchors_used = list(state.get("anchors_used", []))
    if anchor:
        anchors_used.append(f"{court_type}:{workflow}:navigate")

    t0 = time.time()
    try:
        scraper.navigate(page, params)
        duration_ms = int((time.time() - t0) * 1000)

        navigation_registry.record_step(
            court_type, workflow, "navigate",
            selector={"anchor_used": bool(anchor)},
            duration_ms=duration_ms,
            success=True,
        )
        logger.info("[graph] navigate OK court=%s workflow=%s %dms", court_type, workflow, duration_ms)

        return {
            "current_step": "navigate",
            "anchors_used": anchors_used,
        }
    except Exception as e:
        duration_ms = int((time.time() - t0) * 1000)
        navigation_registry.record_step(
            court_type, workflow, "navigate",
            selector={},
            duration_ms=duration_ms,
            success=False,
            fail_reason=str(e),
        )
        logger.error("[graph] navigate failed: %s", e)
        return {
            "error": f"Navigation failed: {e}",
            "current_step": "navigate",
        }
