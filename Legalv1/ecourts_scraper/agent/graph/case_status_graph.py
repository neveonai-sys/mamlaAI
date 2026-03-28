"""
CaseStatusGraph — Level 1 subgraph for case-status searches.

Supports three search methods mapped from UI tabs:
  - "search_party"    (HC only)  params: high_court_id, bench_code, party_name, registration_year, case_status
  - "search_advocate" (HC + DC)  params: differ per court type (see below)
  - "search_cnr"      → delegates to cnr_graph (added for completeness)

HC advocate params: high_court_id, bench_code, advocate_name
DC advocate params: state_id, district_id, court_complex_id, advocate_name

Graph flow:
  classify_request → [hc: acquire_browser, dc: acquire_browser]  (both share identical backbone)
  The difference is the scraper injected at classify_request.
  check_cache → [hit: END, miss: acquire_browser]
  acquire_browser → navigate
  navigate → solve_captcha
  solve_captcha → [solved: fill_form, failed: error_handler]
  fill_form → submit
  submit → [success: parse, captcha_error/blocked/error: error_handler, not_found: END]
  parse → validate → [valid: cache_result → END, invalid: error_handler]
  error_handler → route_recovery → …
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

from ecourts_scraper.agent.graph.state import EcourtsState
from ecourts_scraper.agent.graph.nodes import (
    cache_node, browser_node, navigator_node,
    captcha_node, form_node, submit_node, parser_node, error_handler_node,
)


# ---------------------------------------------------------------------------
# Classify request: pick HC or DC scraper based on params
# ---------------------------------------------------------------------------

def _classify_request(state: dict, config: RunnableConfig) -> dict:
    """
    Determine court type from params and inject the correct scraper into config.

    Decision logic:
    - If params contain "high_court_id"   → HighCourtScraper
    - If params contain "state_id"         → DistrictCourtScraper
    - Else default to HighCourtScraper
    """
    cfg = config["configurable"]
    sb = cfg["sideband"]
    params = state.get("params", {})
    method = params.get("_method", "search_advocate")

    if not sb.get("scraper"):
        if "state_id" in params and "district_id" in params:
            from ecourts_scraper.scrapers.districtcourt import DistrictCourtScraper
            sb["scraper"] = DistrictCourtScraper()
            court_type = "district_court"
        else:
            from ecourts_scraper.scrapers.highcourt import HighCourtScraper
            sb["scraper"] = HighCourtScraper()
            court_type = "high_court"
    else:
        court_type = state.get("court_type", "high_court")

    return {
        "court_type": court_type,
        "workflow": method,
        "current_step": "classify_request",
    }


def _route_cache(state: dict) -> str:
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
# Graph builder
# ---------------------------------------------------------------------------

def build_case_status_graph() -> StateGraph:
    graph = StateGraph(EcourtsState)

    graph.add_node("classify_request", _classify_request)
    graph.add_node("check_cache",      cache_node.check_cache)
    graph.add_node("acquire_browser",  browser_node.acquire_browser)
    graph.add_node("navigate",         navigator_node.navigate)
    graph.add_node("solve_captcha",    captcha_node.solve_captcha)
    graph.add_node("refresh_captcha",  captcha_node.refresh_captcha)
    graph.add_node("fill_form",        form_node.fill_form)
    graph.add_node("submit",           submit_node.submit)
    graph.add_node("parse",            parser_node.parse)
    graph.add_node("validate",         parser_node.validate)
    graph.add_node("cache_result",     cache_node.store_cache)
    graph.add_node("error_handler",    error_handler_node.error_handler)
    graph.add_node("self_heal",        error_handler_node.self_heal)

    graph.set_entry_point("classify_request")
    graph.add_edge("classify_request", "check_cache")
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
    graph.add_edge("parse", "validate")
    graph.add_conditional_edges("validate", parser_node.route_validate, {
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


# Compiled singleton — imported by master_graph
case_status_graph = build_case_status_graph()
