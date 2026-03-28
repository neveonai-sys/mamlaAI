"""
MasterGraph — top-level LangGraph orchestrator for all eCourts searches.

Routing:
  classify → route_search_type → [cnr, case_status, court_orders, causelist, caveat]

Each branch is a compiled subgraph (Level-1 graph) embedded as a single node.
State flows through unchanged — each subgraph reads and mutates EcourtsState.

Usage:
    from ecourts_scraper.agent.graph.master_graph import build_master_graph
    graph = build_master_graph()

    state = make_initial_state(job_id, user_id, "cnr", {"cnr": "MPHC010123456789"})
    config = {"configurable": {"rate_limiter": rate_limiter}}

    for event in graph.stream(state, config):
        node_name = list(event.keys())[0]
        print(f"→ {node_name}")
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging
from langgraph.graph import StateGraph, END

from ecourts_scraper.agent.graph.state import EcourtsState, make_initial_state  # noqa: F401 (re-export convenience)

logger = logging.getLogger("django")

# ---------------------------------------------------------------------------
# Search-type constants — must match what tasks.py / API sends in search_type
# ---------------------------------------------------------------------------

SEARCH_TYPE_CNR          = "cnr"
SEARCH_TYPE_CASE_STATUS  = "case_status"
SEARCH_TYPE_COURT_ORDERS = "court_orders"
SEARCH_TYPE_CAUSELIST    = "causelist"
SEARCH_TYPE_CAVEAT       = "caveat"

_VALID_SEARCH_TYPES = {
    SEARCH_TYPE_CNR,
    SEARCH_TYPE_CASE_STATUS,
    SEARCH_TYPE_COURT_ORDERS,
    SEARCH_TYPE_CAUSELIST,
    SEARCH_TYPE_CAVEAT,
}


# ---------------------------------------------------------------------------
# Classify node — validates search_type and sets workflow
# ---------------------------------------------------------------------------

def _classify(state: dict, config: RunnableConfig) -> dict:
    search_type = state.get("search_type", "")
    if search_type not in _VALID_SEARCH_TYPES:
        logger.warning("[master] unknown search_type=%r, defaulting to cnr", search_type)
        search_type = SEARCH_TYPE_CNR
    return {"search_type": search_type, "current_step": "classify"}


def _route_search_type(state: dict) -> str:
    return state.get("search_type", SEARCH_TYPE_CNR)


# ---------------------------------------------------------------------------
# Finalize node — records metrics, updates job document
# ---------------------------------------------------------------------------

def _finalize(state: dict, config: RunnableConfig) -> dict:
    """
    Called after every successful or failed subgraph run.
    Records metrics to MongoDB and logs the final state.
    """
    job_id = state.get("job_id")
    outcome = "success" if state.get("result") and not state.get("error") else "failure"

    try:
        from ecourts_scraper.agent.registry.step_metrics import record_run
        record_run(
            job_id=job_id,
            search_type=state.get("search_type", ""),
            court_type=state.get("court_type", ""),
            workflow=state.get("workflow", ""),
            outcome=outcome,
            step_log=state.get("step_log", []),
        )
    except Exception as e:
        logger.warning("[master] metrics recording failed: %s", e)

    logger.info(
        "[master] finalize job=%s search_type=%s outcome=%s",
        job_id, state.get("search_type"), outcome,
    )
    return {"current_step": "finalize"}


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_master_graph():
    """
    Build and compile the master LangGraph.

    Each search-type subgraph is imported lazily inside this function to avoid
    module-level Playwright/scraper instantiation at import time.
    """
    from ecourts_scraper.agent.graph.cnr_graph          import cnr_graph
    from ecourts_scraper.agent.graph.case_status_graph  import case_status_graph
    from ecourts_scraper.agent.graph.court_orders_graph import court_orders_graph
    from ecourts_scraper.agent.graph.causelist_graph    import causelist_graph
    from ecourts_scraper.agent.graph.caveat_graph       import caveat_graph

    graph = StateGraph(EcourtsState)

    graph.add_node("classify",       _classify)
    graph.add_node("finalize",       _finalize)

    # Embed compiled subgraphs as nodes
    graph.add_node(SEARCH_TYPE_CNR,          cnr_graph)
    graph.add_node(SEARCH_TYPE_CASE_STATUS,  case_status_graph)
    graph.add_node(SEARCH_TYPE_COURT_ORDERS, court_orders_graph)
    graph.add_node(SEARCH_TYPE_CAUSELIST,    causelist_graph)
    graph.add_node(SEARCH_TYPE_CAVEAT,       caveat_graph)

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        _route_search_type,
        {
            SEARCH_TYPE_CNR:          SEARCH_TYPE_CNR,
            SEARCH_TYPE_CASE_STATUS:  SEARCH_TYPE_CASE_STATUS,
            SEARCH_TYPE_COURT_ORDERS: SEARCH_TYPE_COURT_ORDERS,
            SEARCH_TYPE_CAUSELIST:    SEARCH_TYPE_CAUSELIST,
            SEARCH_TYPE_CAVEAT:       SEARCH_TYPE_CAVEAT,
        },
    )

    # All subgraphs converge at finalize
    for search_type in _VALID_SEARCH_TYPES:
        graph.add_edge(search_type, "finalize")

    graph.add_edge("finalize", END)

    return graph.compile()
