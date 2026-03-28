"""
GraphRunner — thin bridge between Celery tasks and the LangGraph master graph.

Usage in tasks.py:

    from ecourts_scraper.agent.graph.graph_runner import run_graph_task
    ...
    return run_graph_task(
        job_id=job_id,
        user_id=user_id,
        search_type="cnr",
        params={"cnr": cnr, "_method": "case_by_cnr"},
        rate_limiter=hc_rate_limiter,
    )

The runner:
  1. Builds the master graph (lazy, compiled once per process via module cache).
  2. Creates the initial EcourtsState.
  3. Streams graph events — each node transition → update_progress() on the job doc.
  4. Releases the browser context on exit regardless of success/failure.
  5. Returns a Celery-task-compatible dict:  {"status": "completed|failed", ...}
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import logging
import traceback
from functools import lru_cache

logger = logging.getLogger("django")


# ---------------------------------------------------------------------------
# Module-level graph singleton (compiled once per worker process)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_master_graph():
    from ecourts_scraper.agent.graph.master_graph import build_master_graph
    return build_master_graph()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_graph_task(
    *,
    job_id: str,
    user_id: str,
    search_type: str,
    params: dict,
    rate_limiter,
) -> dict:
    """
    Execute the LangGraph master graph for a single eCourts job.

    Parameters
    ----------
    job_id       : MongoDB job document _id string
    user_id      : Supabase user id (for logging / ownership)
    search_type  : one of "cnr", "case_status", "court_orders", "causelist", "caveat"
    params       : search parameters dict (cnr, party_name, etc.)
    rate_limiter : RateLimiter instance for the target court site

    Returns
    -------
    dict  {"status": "completed"|"failed", "job_id": job_id, ...}
    """
    from ecourts_scraper.agent.job_manager import JobManager
    from ecourts_scraper.agent.graph.state import make_initial_state

    jm = JobManager()
    graph = _get_master_graph()
    state = make_initial_state(job_id, user_id, search_type, params)

    # Config sideband: non-serializable objects live here (browser, scraper, rate_limiter).
    # LangGraph shallow-copies config["configurable"] between nodes, so top-level keys set
    # inside one node are NOT visible in the next.  The fix: put mutable objects that need
    # to be shared across nodes inside a single dict ("sideband") — the dict object is the
    # same Python reference across all nodes because shallow copy preserves value references.
    sideband: dict = {
        "browser_ctx": None,   # acquire_browser node fills this
        "page": None,          # acquire_browser node fills this
        "scraper": None,       # resolve_court / classify node fills this
    }
    config: dict = {
        "configurable": {
            "rate_limiter": rate_limiter,
            "job_manager": jm,
            "sideband": sideband,  # shared mutable container
        }
    }

    final_state: dict = {}

    try:
        jm.update_progress(job_id, "processing", "classify", agent_state="classify")

        # Stream graph events — each event is {node_name: state_delta}
        for event in graph.stream(state, config, stream_mode="updates"):
            node_name = list(event.keys())[0] if event else "unknown"
            node_delta = event.get(node_name, {})

            # Propagate step update to MongoDB (read by frontend poll)
            current_step = node_delta.get("current_step", node_name)
            _emit_progress(jm, job_id, current_step, node_delta)

            # Merge delta into state so we can read final values
            final_state.update(node_delta)

        # Determine outcome from merged final state
        result = final_state.get("result")
        error  = final_state.get("error")

        if result and not error:
            jm.complete_job(job_id, result)
            return {"status": "completed", "job_id": job_id, "cached": final_state.get("cache_hit", False)}
        else:
            reason = error or "Graph completed without result"
            jm.fail_job(job_id, reason)
            return {"status": "failed", "job_id": job_id, "error": reason}

    except Exception as e:
        logger.error(
            "[graph_runner] graph crashed job=%s search_type=%s: %s\n%s",
            job_id, search_type, e, traceback.format_exc(),
        )
        try:
            jm.fail_job(job_id, str(e))
        except Exception:
            pass
        return {"status": "failed", "job_id": job_id, "error": str(e)}

    finally:
        # Always release the browser context acquired during the graph run
        _cleanup_browser(config)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _emit_progress(jm, job_id: str, step: str, delta: dict):
    """Push a lightweight progress update to the job document."""
    try:
        jm.update_progress(
            job_id,
            "processing",
            step,
            agent_state=step,
        )
    except Exception as e:
        logger.debug("[graph_runner] progress update failed step=%s: %s", step, e)


def _cleanup_browser(config: dict):
    """Release browser context back to the pool after graph completes."""
    cfg = config.get("configurable", {})
    browser_ctx = cfg.get("browser_ctx")
    if browser_ctx is None:
        return
    try:
        from ecourts_scraper.infra.browser_pool import browser_pool
        browser_pool.release_context(browser_ctx)
        logger.debug("[graph_runner] browser context released")
    except Exception as e:
        logger.warning("[graph_runner] browser release failed: %s", e)
