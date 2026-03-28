"""
Shared state schema for all LangGraph eCourts agent graphs.

Key design constraints:
- Browser context (Playwright Page/BrowserContext) is NOT in state — non-serializable.
  It lives in config["configurable"]["browser_ctx"] as a sideband.
- All scalar/serializable fields live in EcourtsState.
- step_log accumulates per-step timing for the learning registry.
"""
from __future__ import annotations
from typing import TypedDict, Any, Optional


class StepEntry(TypedDict):
    name: str
    started_at: str       # ISO8601
    duration_ms: int
    status: str           # success | failed | skipped
    detail: str           # short human-readable note


class EcourtsState(TypedDict, total=False):
    # ── job identity ─────────────────────────────────────────────
    job_id: str
    user_id: str
    search_type: str      # cnr | case_status | court_orders | causelist | caveat
    court_type: str       # high_court | district_court (resolved by subgraph)
    workflow: str         # detailed method key, e.g. "search_party", "case_by_cnr"

    # ── request params ────────────────────────────────────────────
    params: dict[str, Any]

    # ── execution state ───────────────────────────────────────────
    current_step: str
    step_log: list[StepEntry]
    submit_outcome: str   # success | captcha_error | blocked | not_found | error
    error: Optional[str]

    # ── retry counters ────────────────────────────────────────────
    captcha_attempts: int
    proxy_retries: int
    total_retries: int

    # ── result ───────────────────────────────────────────────────
    result: Optional[dict[str, Any]]
    cache_hit: bool

    # ── learning registry metadata ────────────────────────────────
    anchors_used: list[str]        # which anchor selectors were used
    captcha_strategy_used: str     # which captcha method succeeded


# ─── Human-readable step labels for the frontend StepIndicator ──────────────
STEP_LABELS: dict[str, str] = {
    "classify_request":   "Routing request",
    "check_cache":        "Checking cache",
    "acquire_browser":    "Starting browser",
    "navigate":           "Navigating to court",
    "select_court":       "Selecting court",
    "fill_date":          "Setting date",
    "solve_captcha":      "Solving CAPTCHA",
    "refresh_captcha":    "Refreshing CAPTCHA",
    "fill_form":          "Filling form",
    "submit":             "Submitting",
    "parse":              "Parsing results",
    "validate":           "Validating data",
    "cache_result":       "Saving to cache",
    "finalize":           "Finalizing",
    # error recovery
    "retry_captcha":      "Retrying CAPTCHA",
    "rotate_proxy":       "Rotating connection",
    "backoff":            "Waiting before retry",
    "self_heal":          "Auto-healing selector",
    "error_handler":      "Handling error",
    # search type routing
    "cnr_subgraph":       "CNR lookup",
    "case_status_subgraph": "Case status search",
    "court_orders_subgraph": "Loading orders",
    "causelist_subgraph": "Loading cause list",
    "caveat_subgraph":    "Caveat search",
    "done":               "Done",
}


def label_for(step: str) -> str:
    return STEP_LABELS.get(step, step.replace("_", " ").title())


# ─── Initial state factory ────────────────────────────────────────────────────
def make_initial_state(
    job_id: str,
    user_id: str,
    search_type: str,
    params: dict,
) -> EcourtsState:
    return EcourtsState(
        job_id=job_id,
        user_id=user_id,
        search_type=search_type,
        court_type="",
        workflow="",
        params=params,
        current_step="classify_request",
        step_log=[],
        submit_outcome="",
        error=None,
        captcha_attempts=0,
        proxy_retries=0,
        total_retries=0,
        result=None,
        cache_hit=False,
        anchors_used=[],
        captcha_strategy_used="",
    )
