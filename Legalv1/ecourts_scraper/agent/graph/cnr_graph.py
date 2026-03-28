"""
CNRGraph — Level 1 subgraph for CNR lookup.

Input params: {"cnr": "<CNR>", "_method": "case_by_cnr"}
Court type auto-detected from CNR prefix (HC if "HC" in first 6 chars, else DC).

Graph flow:
  check_cache → [hit: END, miss: acquire_browser]
  acquire_browser → navigate → solve_captcha
  solve_captcha → [solved: fill_form, failed: error_handler]
  fill_form → submit
  submit → [success: parse, captcha_error/blocked/error: error_handler, not_found: END]
  parse → validate → [valid: cache_result → END, invalid: error_handler]
  error_handler → [retry_captcha → refresh_captcha → solve_captcha,
                    rotate_proxy/backoff → acquire_browser,
                    self_heal → navigate,
                    give_up → END]
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

from ecourts_scraper.agent.graph.state import EcourtsState
from ecourts_scraper.agent.graph.nodes import (
    cache_node, browser_node, navigator_node,
    captcha_node, form_node, submit_node, parser_node, error_handler_node,
)


def _resolve_court_type(state: dict, config: RunnableConfig) -> dict:
    """Auto-detect HC vs DC from CNR prefix and instantiate correct scraper."""
    cnr = state.get("params", {}).get("cnr", "")
    cnr_upper = cnr.upper()
    court_type = "high_court" if (len(cnr_upper) >= 4 and "HC" in cnr_upper[:6]) else "district_court"

    # Lazy scraper instantiation — put in sideband (mutable container shared across nodes)
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
        "workflow": "case_by_cnr",
        "current_step": "classify_court",
    }


def _route_cache(state: dict) -> str:
    return "__end__" if state.get("cache_hit") else "acquire_browser"


def _route_captcha(state: dict) -> str:
    # If captcha_attempts was incremented (failure), go to error_handler
    # If not (success), go to fill_form
    # We detect failure by checking if error is set or captcha_attempts > 0 AND
    # current_step == solve_captcha AND no change in submit_outcome
    captcha_attempts = state.get("captcha_attempts", 0)
    error = state.get("error")
    if error and "captcha" in error.lower():
        return "error_handler"
    # If solve_captcha didn't set captcha_strategy_used, it failed (attempts incremented)
    if not state.get("captcha_strategy_used") and captcha_attempts > 0:
        return "error_handler"
    return "fill_form"


def build_cnr_graph() -> StateGraph:
    graph = StateGraph(EcourtsState)

    graph.add_node("resolve_court",   _resolve_court_type)
    graph.add_node("check_cache",     cache_node.check_cache)
    graph.add_node("acquire_browser", browser_node.acquire_browser)
    graph.add_node("navigate",        navigator_node.navigate)
    graph.add_node("solve_captcha",   captcha_node.solve_captcha)
    graph.add_node("refresh_captcha", captcha_node.refresh_captcha)
    graph.add_node("fill_form",       form_node.fill_form)
    graph.add_node("submit",          submit_node.submit)
    graph.add_node("parse",           parser_node.parse)
    graph.add_node("validate",        parser_node.validate)
    graph.add_node("cache_result",    cache_node.store_cache)
    graph.add_node("error_handler",   error_handler_node.error_handler)
    graph.add_node("self_heal",       error_handler_node.self_heal)

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
cnr_graph = build_cnr_graph()
