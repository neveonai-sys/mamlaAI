"""
CaveatGraph — Level 1 subgraph for caveat searches.

Status: NOT IMPLEMENTED — eCourts caveat search API endpoint is not yet
reverse-engineered.  This stub returns immediately with a graceful
"not_implemented" result so the master graph can route it without crashing.

When caveat scraping is ready, replace _caveat_stub with a full graph similar
to CaseStatusGraph.
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging
from langgraph.graph import StateGraph, END

from ecourts_scraper.agent.graph.state import EcourtsState

logger = logging.getLogger("django")


def _caveat_stub(state: dict, config: RunnableConfig) -> dict:
    logger.info("[graph] caveat search not yet implemented — returning stub")
    return {
        "result": {
            "status": "not_implemented",
            "message": "Caveat search is not yet available. Please check back later.",
        },
        "current_step": "caveat_stub",
    }


def build_caveat_graph() -> StateGraph:
    graph = StateGraph(EcourtsState)
    graph.add_node("caveat_stub", _caveat_stub)
    graph.set_entry_point("caveat_stub")
    graph.add_edge("caveat_stub", END)
    return graph.compile()


# Compiled singleton
caveat_graph = build_caveat_graph()
