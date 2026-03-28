"""
ErrorHandlerNode — classify errors and decide the recovery path.

error_handler(state, config) → state delta
  Looks at submit_outcome, error, and retry counters to decide what to do next.
  Sets state["_recovery_action"] which is used by the conditional edge router.

Recovery actions:
  retry_captcha  → refresh captcha and try solve again
  rotate_proxy   → release browser, get new proxy, acquire new browser
  backoff        → sleep, then re-navigate from scratch
  self_heal      → invoke LLM self-heal for broken selectors
  give_up        → too many retries, fail the job
"""
from __future__ import annotations
from langchain_core.runnables import RunnableConfig
import time
import logging

logger = logging.getLogger("django")

MAX_CAPTCHA_RETRIES = 10
MAX_PROXY_ROTATIONS = 3
MAX_TOTAL_RETRIES = 3
MAX_SELF_HEAL_ATTEMPTS = 2


def error_handler(state: dict, config: RunnableConfig) -> dict:
    """Classify the error and determine recovery action."""
    outcome = state.get("submit_outcome", "")
    error = state.get("error", "")
    captcha_attempts = state.get("captcha_attempts", 0)
    proxy_retries = state.get("proxy_retries", 0)
    total_retries = state.get("total_retries", 0)

    logger.warning(
        "[graph] error_handler outcome=%s err=%s captcha=%d proxy=%d total=%d",
        outcome, error[:80] if error else "", captcha_attempts, proxy_retries, total_retries
    )

    # ── CAPTCHA error path ────────────────────────────────────────
    if outcome == "captcha_error" or "captcha" in (error or "").lower():
        if captcha_attempts < MAX_CAPTCHA_RETRIES:
            return {"_recovery_action": "retry_captcha", "current_step": "error_handler"}
        return {
            "_recovery_action": "give_up",
            "error": f"CAPTCHA failed after {captcha_attempts} attempts",
            "current_step": "error_handler",
        }

    # ── IP blocked / rate limited ─────────────────────────────────
    if outcome == "blocked":
        if proxy_retries < MAX_PROXY_ROTATIONS:
            # Release current browser — acquire_browser will get a fresh proxy
            _release_current_browser(config)
            return {
                "_recovery_action": "rotate_proxy",
                "proxy_retries": proxy_retries + 1,
                "current_step": "error_handler",
            }
        return {
            "_recovery_action": "give_up",
            "error": "Blocked by court site after 3 proxy rotations",
            "current_step": "error_handler",
        }

    # ── Selector/locator broken → try self-heal ───────────────────
    if _looks_like_selector_error(error):
        self_heal_count = config["configurable"].get("self_heal_attempts", 0)
        if self_heal_count < MAX_SELF_HEAL_ATTEMPTS:
            config["configurable"]["self_heal_attempts"] = self_heal_count + 1
            return {"_recovery_action": "self_heal", "current_step": "error_handler"}

    # ── Generic error → backoff + retry ──────────────────────────
    if total_retries < MAX_TOTAL_RETRIES:
        backoff_s = min(2 ** total_retries * 2, 30)
        logger.info("[graph] backing off %ds before retry", backoff_s)
        time.sleep(backoff_s)
        _release_current_browser(config)
        return {
            "_recovery_action": "backoff",
            "total_retries": total_retries + 1,
            "current_step": "error_handler",
        }

    return {
        "_recovery_action": "give_up",
        "error": error or "Max retries reached",
        "current_step": "error_handler",
    }


def self_heal(state: dict, config: RunnableConfig) -> dict:
    """Invoke LLM self-heal for a broken selector."""
    from ecourts_scraper.agent.self_heal import attempt_self_heal

    cfg = config["configurable"]
    sb = cfg["sideband"]
    scraper = sb["scraper"]
    page = sb.get("page")
    error = state.get("error", "")

    if not page:
        return {"_recovery_action": "give_up", "current_step": "self_heal"}

    try:
        healed = attempt_self_heal(
            page=page,
            site=scraper.get_source_site(),
            page_name=state.get("workflow", "unknown"),
            element_name="broken_element",
            broken_selector={"value": "", "by": "css"},
            error_message=error,
        )
        if healed:
            logger.info("[graph] self_heal succeeded")
            _release_current_browser(config)
            return {"_recovery_action": "backoff", "current_step": "self_heal"}
    except Exception as e:
        logger.error("[graph] self_heal failed: %s", e)

    return {
        "_recovery_action": "give_up",
        "error": "Self-heal could not recover the selector",
        "current_step": "self_heal",
    }


# ─── Edge router ──────────────────────────────────────────────────────────────
def route_recovery(state: dict) -> str:
    """Conditional edge: maps _recovery_action → next node name."""
    action = state.get("_recovery_action", "give_up")
    routes = {
        "retry_captcha": "refresh_captcha",
        "rotate_proxy": "acquire_browser",
        "backoff": "navigate",
        "self_heal": "self_heal",
        "give_up": "__end__",
    }
    return routes.get(action, "__end__")


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _looks_like_selector_error(error: str | None) -> bool:
    if not error:
        return False
    keywords = ["strict mode violation", "locator.element_handle", "timeout", "not found selector"]
    return any(k in error.lower() for k in keywords)


def _release_current_browser(config: dict) -> None:
    from ecourts_scraper.infra.browser_pool import browser_pool
    cfg = config.get("configurable", {})
    sb = cfg.get("sideband", {})
    ctx = sb.get("browser_ctx")
    if ctx:
        try:
            browser_pool.release_context(ctx)
        except Exception:
            pass
        sb["browser_ctx"] = None
        sb["page"] = None
