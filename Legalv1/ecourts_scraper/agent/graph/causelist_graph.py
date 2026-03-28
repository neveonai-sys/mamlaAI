"""
CauseListGraph — Level 1 subgraph for HC daily cause lists.

IMPORTANT: The HC cause-list section renders its captcha ONLY AFTER the date
input fires a JS change event.  Therefore date filling happens inside
CauseListScraper.navigate() — NOT in fill_form().

params must include:
  - _method       = "causelist"
  - high_court_id (HC state code, e.g. "2")
  - bench_code    (bench/court complex code)
  - date          (YYYY-MM-DD format)

Graph flow:
  resolve_court → check_cache
   ├─ hit  → END
   └─ miss → acquire_browser → navigate (fills date inside navigate())
              → solve_captcha
              → [solved: fill_form (no-op), failed: error_handler]
              → submit
              → [success: parse → validate → cache_result → END]
              → [captcha_error/error: error_handler]
              → [not_found: END]
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


def _resolve_court(state: dict, config: RunnableConfig) -> dict:
    """Always uses CauseListScraper (HC-only)."""
    cfg = config["configurable"]
    sb = cfg["sideband"]
    if not sb.get("scraper"):
        from ecourts_scraper.scrapers.causelist import CauseListScraper
        sb["scraper"] = CauseListScraper()
    return {
        "court_type": "high_court",
        "workflow": "causelist",
        "current_step": "resolve_court",
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


def build_causelist_graph() -> StateGraph:
    graph = StateGraph(EcourtsState)

    graph.add_node("resolve_court",   _resolve_court)
    graph.add_node("check_cache",     cache_node.check_cache)
    graph.add_node("acquire_browser", browser_node.acquire_browser)
    # navigate() calls CauseListScraper.navigate() which fills the date field
    # internally before returning — captcha renders after that JS event
    graph.add_node("navigate",        navigator_node.navigate)
    graph.add_node("solve_captcha",   captcha_node.solve_captcha)
    graph.add_node("refresh_captcha", captcha_node.refresh_captcha)
    # fill_form is a no-op for causelist (date already filled in navigate)
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


# Compiled singleton
causelist_graph = build_causelist_graph()
