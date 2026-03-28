"""
CourtOrdersGraph — Level 1 subgraph for fetching court orders.

Two-phase flow:
  Phase 1  — get case detail (may hit CNR cache or run cnr_graph if needed)
  Phase 2  — navigate to the orders sub-page and parse the orders table

Because Phase 1 can reuse the cnr_graph entirely, we call it as a regular Python
function rather than a nested LangGraph subgraph — this avoids double-browser
acquisition.  If the case result is already in our MongoDB cache the browser
is acquired only once (for Phase 2).

Graph flow:
  check_case_cache
   ├─ hit  → acquire_browser → navigate_orders → solve_captcha → submit → parse_orders → validate → cache_result → END
   └─ miss → acquire_browser → navigate (CNR page) → solve_captcha → fill_form → submit_cnr
                → parse_cnr (stores in state) → navigate_orders → solve_captcha → submit → parse_orders → …

For simplicity we use a single linear flow: resolve the CNR first (via the
navigate / captcha / fillform / submit / parse nodes), then navigate to the
orders page.  The orders page on hcservices.ecourts.gov.in is reached from the
case detail page by clicking the orders tab — so we treat it as a continuation
of the same browser session.

params must include:
  - cnr           (always)
  - _method       = "court_orders"
  - order_type    = "all" | "interim" | "final"  (optional, default "all")
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging
from langgraph.graph import StateGraph, END

from ecourts_scraper.agent.graph.state import EcourtsState
from ecourts_scraper.agent.graph.nodes import (
    cache_node, browser_node, navigator_node,
    captcha_node, form_node, submit_node, parser_node, error_handler_node,
)

logger = logging.getLogger("django")


# ---------------------------------------------------------------------------
# Resolve court type and scraper from CNR
# ---------------------------------------------------------------------------

def _resolve_court(state: dict, config: RunnableConfig) -> dict:
    cnr = state.get("params", {}).get("cnr", "")
    cnr_upper = cnr.upper()
    court_type = "high_court" if "HC" in cnr_upper[:6] else "district_court"

    cfg = config["configurable"]
    sb = cfg["sideband"]
    if not sb.get("scraper"):
        if court_type == "high_court":
            from ecourts_scraper.scrapers.highcourt import HighCourtScraper
            sb["scraper"] = HighCourtScraper()
        else:
            from ecourts_scraper.scrapers.districtcourt import DistrictCourtScraper
            sb["scraper"] = DistrictCourtScraper()

    return {
        "court_type": court_type,
        "workflow": "court_orders",
        "current_step": "resolve_court",
    }


def _route_cache(state: dict) -> str:
    # If CNR case detail is already cached we can skip straight to orders navigation.
    # For now: cache hit on case_detail means we already have orders too (stored together by
    # HighCourtScraper._parse_case_detail which includes result["orders"]).
    return "__end__" if state.get("cache_hit") else "acquire_browser"


def _route_captcha(state: dict) -> str:
    captcha_attempts = state.get("captcha_attempts", 0)
    error = state.get("error")
    if error and "captcha" in error.lower():
        return "error_handler"
    if not state.get("captcha_strategy_used") and captcha_attempts > 0:
        return "error_handler"
    return "fill_form"


# ---------------------------------------------------------------------------
# Orders navigation node — runs AFTER the base case is parsed.
# The orders tab is accessible on the same page once the case detail is loaded,
# so we just navigate to it from the current page state.
# ---------------------------------------------------------------------------

def _navigate_orders(state: dict, config: RunnableConfig) -> dict:
    """Click the 'Orders' tab on the HC case detail page."""
    cfg = config["configurable"]
    page = cfg["sideband"].get("page")
    if not page:
        return {"error": "No page for orders navigation", "current_step": "navigate_orders"}

    try:
        # HC orders tab selector — hcservices.ecourts.gov.in
        from ecourts_scraper.infra.parsers import click_element, element_exists
        import time

        # Try to click the orders tab (present on case detail page)
        if element_exists(page, "a[href*='order'], a:has-text('Orders'), #orders_tab", "css", timeout=3000):
            click_element(page, "a[href*='order'], a:has-text('Orders'), #orders_tab", "css", timeout=5000)
            time.sleep(1)
        # Else orders are already rendered in the current parse (as result["orders"])
        logger.info("[graph] navigate_orders OK cnr=%s", state.get("params", {}).get("cnr"))
        return {"current_step": "navigate_orders"}
    except Exception as e:
        logger.warning("[graph] navigate_orders error: %s", e)
        return {"current_step": "navigate_orders"}  # Non-fatal; orders may be on main page


def _parse_orders(state: dict, config: RunnableConfig) -> dict:
    """Extract orders from the already-parsed result or the current page."""
    result = state.get("result") or {}

    # Orders may already be embedded in the CNR parse result
    orders = result.get("orders", [])
    if orders:
        return {"result": {"orders": orders, "_source": "embedded"}, "current_step": "parse_orders"}

    # Fallback: parse orders table directly from page
    cfg = config["configurable"]
    page = cfg["sideband"].get("page")
    if not page:
        return {"result": {"orders": [], "_source": "no_page"}, "current_step": "parse_orders"}

    try:
        from ecourts_scraper.infra.parsers import get_table_as_dicts
        orders_data = get_table_as_dicts(page, "table.order_table", "css", timeout=5000) or []
        return {"result": {"orders": orders_data}, "current_step": "parse_orders"}
    except Exception as e:
        logger.warning("[graph] parse_orders error: %s", e)
        return {"result": {"orders": []}, "current_step": "parse_orders"}


def _validate_orders(state: dict, config: RunnableConfig) -> dict:
    result = state.get("result") or {}
    if "orders" in result:
        return {"current_step": "validate_orders"}
    return {"error": "No orders data parsed", "current_step": "validate_orders"}


def _route_validate_orders(state: dict) -> str:
    if state.get("error") and "No orders" in state.get("error", ""):
        return "error_handler"
    return "cache_result"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_court_orders_graph() -> StateGraph:
    graph = StateGraph(EcourtsState)

    graph.add_node("resolve_court",    _resolve_court)
    graph.add_node("check_cache",      cache_node.check_cache)
    graph.add_node("acquire_browser",  browser_node.acquire_browser)
    graph.add_node("navigate",         navigator_node.navigate)     # navigate to CNR page
    graph.add_node("solve_captcha",    captcha_node.solve_captcha)
    graph.add_node("refresh_captcha",  captcha_node.refresh_captcha)
    graph.add_node("fill_form",        form_node.fill_form)
    graph.add_node("submit",           submit_node.submit)
    graph.add_node("parse",            parser_node.parse)            # parse CNR case detail
    graph.add_node("navigate_orders",  _navigate_orders)             # click orders tab
    graph.add_node("parse_orders",     _parse_orders)
    graph.add_node("validate_orders",  _validate_orders)
    graph.add_node("cache_result",     cache_node.store_cache)
    graph.add_node("error_handler",    error_handler_node.error_handler)
    graph.add_node("self_heal",        error_handler_node.self_heal)

    graph.set_entry_point("resolve_court")
    graph.add_edge("resolve_court", "check_cache")
    graph.add_conditional_edges("check_cache", _route_cache, {
        "acquire_browser": "acquire_browser",
        "__end__": END,
    })
    graph.add_edge("acquire_browser", "navigate")
    graph.add_edge("navigate", "solve_captcha")
    graph.add_conditional_edges("solve_captcha", _route_captcha, {
        "fill_form": "fill_form",
        "error_handler": "error_handler",
    })
    graph.add_edge("refresh_captcha", "solve_captcha")
    graph.add_edge("fill_form", "submit")
    graph.add_conditional_edges("submit", submit_node.route_submit_outcome, {
        "parse": "parse",
        "error_handler": "error_handler",
        "__end__": END,
    })
    graph.add_edge("parse", "navigate_orders")
    graph.add_edge("navigate_orders", "parse_orders")
    graph.add_edge("parse_orders", "validate_orders")
    graph.add_conditional_edges("validate_orders", _route_validate_orders, {
        "cache_result": "cache_result",
        "error_handler": "error_handler",
    })
    graph.add_edge("cache_result", END)
    graph.add_conditional_edges("error_handler", error_handler_node.route_recovery, {
        "refresh_captcha": "refresh_captcha",
        "acquire_browser": "acquire_browser",
        "navigate": "navigate",
        "self_heal": "self_heal",
        "__end__": END,
    })
    graph.add_conditional_edges("self_heal", error_handler_node.route_recovery, {
        "backoff": "navigate",
        "__end__": END,
    })

    return graph.compile()


# Compiled singleton
court_orders_graph = build_court_orders_graph()
