"""
ScrapeAgent: Deterministic state machine for eCourts scraping jobs.

Each scraping operation (case lookup, search, cause list) is executed
as a state machine with automatic recovery:
  CHECK_CACHE -> ACQUIRE_BROWSER -> SELECT_PROXY -> NAVIGATE ->
  SOLVE_CAPTCHA -> FILL_FORM -> SUBMIT -> PARSE -> VALIDATE -> CACHE

Recovery transitions:
  - CAPTCHA failure -> retry CAPTCHA (up to 5) -> fallback to 2Captcha
  - IP blocked -> rotate proxy -> retry from NAVIGATE
  - Timeout -> exponential backoff -> retry from NAVIGATE
  - Selector broken -> escalate to self-heal (Layer 3)
"""
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ecourts_scraper.infra.rate_limiter import RateLimiter
from ecourts_scraper.agent.job_manager import JobManager
from ecourts_scraper.constants import MAX_AGENT_RETRIES

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page
    from ecourts_scraper.infra.proxy import ProxyManager

logger = logging.getLogger("django")

_proxy_manager = None


def _get_proxy_manager():
    global _proxy_manager
    if _proxy_manager is None:
        from ecourts_scraper.infra.proxy import ProxyManager
        _proxy_manager = ProxyManager()
    return _proxy_manager


class AgentState(Enum):
    CHECK_CACHE = "check_cache"
    ACQUIRE_BROWSER = "acquire_browser"
    SELECT_PROXY = "select_proxy"
    NAVIGATE = "navigate"
    SOLVE_CAPTCHA = "solve_captcha"
    FILL_FORM = "fill_form"
    SUBMIT = "submit"
    PARSE = "parse"
    VALIDATE = "validate"
    CACHE_RESULT = "cache_result"
    RETURN_RESULT = "return_result"
    ROTATE_PROXY = "rotate_proxy"
    RETRY_CAPTCHA = "retry_captcha"
    BACKOFF = "backoff"
    SELF_HEAL = "self_heal"
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass
class AgentContext:
    """Mutable context passed through state transitions."""
    job_id: str
    scraper_name: str
    scraper_method: str
    params: dict
    rate_limiter: RateLimiter

    # Runtime state
    state: AgentState = AgentState.CHECK_CACHE
    context: Any = None  # BrowserContext
    page: Any = None     # Page
    proxy_config: dict | None = None
    captcha_attempts: int = 0
    navigation_retries: int = 0
    total_retries: int = 0
    backoff_seconds: float = 2.0
    result: dict | None = None
    error: str | None = None
    cached: bool = False


class ScrapeAgent:
    """
    Executes a scraping job as a state machine.
    The actual scraping logic (navigate, fill form, parse) is delegated
    to the scraper instance passed in -- this class handles the lifecycle,
    recovery, and state transitions.
    """

    def __init__(self, scraper, job_manager: JobManager):
        """
        Args:
            scraper: An instance of BaseScraper subclass (HighCourtScraper, etc.)
            job_manager: For persisting job status updates
        """
        self.scraper = scraper
        self.job_manager = job_manager

    def execute(self, ctx: AgentContext) -> dict | None:
        """
        Run the state machine to completion.
        Returns the scraped result dict or None on failure.
        """
        while ctx.state not in (AgentState.COMPLETED, AgentState.FAILED):
            logger.debug("[%s] State: %s", ctx.job_id, ctx.state.value)
            self.job_manager.update_progress(
                ctx.job_id, "processing", ctx.state.value,
                agent_state=ctx.state.value,
            )

            try:
                handler = self._get_handler(ctx.state)
                handler(ctx)
            except Exception as e:
                logger.error("[%s] Error in state %s: %s", ctx.job_id, ctx.state.value, e)
                self._handle_exception(ctx, e)

        if ctx.state == AgentState.COMPLETED:
            return ctx.result
        return None

    def _get_handler(self, state: AgentState):
        handlers = {
            AgentState.CHECK_CACHE: self._check_cache,
            AgentState.ACQUIRE_BROWSER: self._acquire_browser,
            AgentState.SELECT_PROXY: self._select_proxy,
            AgentState.NAVIGATE: self._navigate,
            AgentState.SOLVE_CAPTCHA: self._solve_captcha,
            AgentState.FILL_FORM: self._fill_form,
            AgentState.SUBMIT: self._submit,
            AgentState.PARSE: self._parse,
            AgentState.VALIDATE: self._validate,
            AgentState.CACHE_RESULT: self._cache_result,
            AgentState.RETURN_RESULT: self._return_result,
            AgentState.ROTATE_PROXY: self._rotate_proxy,
            AgentState.RETRY_CAPTCHA: self._retry_captcha,
            AgentState.BACKOFF: self._backoff,
            AgentState.SELF_HEAL: self._self_heal,
        }
        return handlers[state]

    # -----------------------------------------------------------------------
    # State handlers
    # -----------------------------------------------------------------------

    def _check_cache(self, ctx: AgentContext):
        from ecourts_scraper.cache.cache_manager import EcourtsCacheManager
        cache = EcourtsCacheManager()
        cache_key = self.scraper.build_cache_key(ctx.scraper_method, ctx.params)
        cached = cache.get(cache_key)
        if cached:
            ctx.result = cached["data"]
            ctx.cached = True
            ctx.state = AgentState.COMPLETED
        else:
            ctx.state = AgentState.ACQUIRE_BROWSER

    def _acquire_browser(self, ctx: AgentContext):
        from ecourts_scraper.infra.browser_pool import _is_gevent_patched, run_scrape_in_subprocess
        if _is_gevent_patched():
            # gevent is active – run entire scrape in a clean subprocess
            scraper_cls = type(self.scraper)
            scraper_path = f"{scraper_cls.__module__}.{scraper_cls.__name__}"
            ctx.result = run_scrape_in_subprocess(scraper_path, ctx.scraper_method, ctx.params)
            ctx.state = AgentState.VALIDATE
            return
        from ecourts_scraper.infra.browser_pool import browser_pool
        pm = _get_proxy_manager()
        proxy = pm.get_proxy() if pm.has_proxies else None
        ctx.proxy_config = proxy
        ctx.context = browser_pool.acquire_context(proxy=proxy)
        ctx.page = browser_pool.new_page(ctx.context)
        ctx.state = AgentState.SELECT_PROXY

    def _select_proxy(self, ctx: AgentContext):
        if not ctx.rate_limiter.acquire(timeout=60):
            ctx.error = "Rate limit timeout"
            ctx.state = AgentState.FAILED
            return
        ctx.state = AgentState.NAVIGATE

    def _navigate(self, ctx: AgentContext):
        self.scraper.navigate(ctx.page, ctx.params)
        ctx.state = AgentState.SOLVE_CAPTCHA

    def _solve_captcha(self, ctx: AgentContext):
        solved = self.scraper.solve_captcha(ctx.page, ctx.captcha_attempts)
        if solved:
            ctx.state = AgentState.FILL_FORM
        else:
            ctx.state = AgentState.RETRY_CAPTCHA

    def _fill_form(self, ctx: AgentContext):
        self.scraper.fill_form(ctx.page, ctx.params)
        ctx.state = AgentState.SUBMIT

    def _submit(self, ctx: AgentContext):
        submit_result = self.scraper.submit_and_check(ctx.page)
        if submit_result == "success":
            ctx.state = AgentState.PARSE
        elif submit_result == "captcha_error":
            ctx.state = AgentState.RETRY_CAPTCHA
        elif submit_result == "blocked":
            ctx.state = AgentState.ROTATE_PROXY
        elif submit_result == "not_found":
            ctx.result = {"status": "not_found", "data": None}
            ctx.state = AgentState.COMPLETED
        else:
            ctx.state = AgentState.BACKOFF

    def _parse(self, ctx: AgentContext):
        ctx.result = self.scraper.parse_results(ctx.page, ctx.params)
        ctx.state = AgentState.VALIDATE

    def _validate(self, ctx: AgentContext):
        if ctx.result and self.scraper.validate_result(ctx.result):
            ctx.state = AgentState.CACHE_RESULT
        else:
            ctx.total_retries += 1
            if ctx.total_retries < MAX_AGENT_RETRIES:
                ctx.state = AgentState.BACKOFF
            else:
                ctx.error = "Validation failed after max retries"
                ctx.state = AgentState.FAILED

    def _cache_result(self, ctx: AgentContext):
        from ecourts_scraper.cache.cache_manager import EcourtsCacheManager
        cache = EcourtsCacheManager()
        cache_key = self.scraper.build_cache_key(ctx.scraper_method, ctx.params)
        data_type = self.scraper.get_data_type(ctx.scraper_method)
        source_site = self.scraper.get_source_site()
        cache.set(cache_key, data_type, ctx.result, source_site)
        ctx.state = AgentState.RETURN_RESULT

    def _return_result(self, ctx: AgentContext):
        ctx.state = AgentState.COMPLETED

    def _rotate_proxy(self, ctx: AgentContext):
        from ecourts_scraper.infra.browser_pool import browser_pool
        pm = _get_proxy_manager()
        if ctx.proxy_config:
            pm.mark_unhealthy(ctx.proxy_config["server"])

        self._cleanup_browser(ctx)

        ctx.navigation_retries += 1
        if ctx.navigation_retries >= MAX_AGENT_RETRIES:
            ctx.error = "Max proxy rotations exceeded"
            ctx.state = AgentState.FAILED
            return

        new_proxy = pm.get_proxy() if pm.has_proxies else None
        ctx.proxy_config = new_proxy
        ctx.context = browser_pool.acquire_context(proxy=new_proxy)
        ctx.page = browser_pool.new_page(ctx.context)
        ctx.state = AgentState.SELECT_PROXY

    def _retry_captcha(self, ctx: AgentContext):
        ctx.captcha_attempts += 1
        from ecourts_scraper.constants import CAPTCHA_MAX_TOTAL_RETRIES
        if ctx.captcha_attempts >= CAPTCHA_MAX_TOTAL_RETRIES:
            ctx.error = f"CAPTCHA failed after {ctx.captcha_attempts} attempts"
            ctx.state = AgentState.FAILED
            return
        try:
            self.scraper.refresh_captcha(ctx.page)
        except Exception:
            pass
        ctx.state = AgentState.SOLVE_CAPTCHA

    def _backoff(self, ctx: AgentContext):
        from ecourts_scraper.infra.browser_pool import browser_pool
        wait = min(ctx.backoff_seconds, 30.0)
        logger.info("[%s] Backing off %.1fs", ctx.job_id, wait)
        time.sleep(wait)
        ctx.backoff_seconds *= 2
        self._cleanup_browser(ctx)
        ctx.context = browser_pool.acquire_context(proxy=ctx.proxy_config)
        ctx.page = browser_pool.new_page(ctx.context)
        ctx.state = AgentState.NAVIGATE

    def _self_heal(self, ctx: AgentContext):
        from ecourts_scraper.constants import SELF_HEAL_ENABLED, SELF_HEAL_MAX_RETRIES
        if not SELF_HEAL_ENABLED:
            ctx.error = "Selector broken and self-heal disabled"
            ctx.state = AgentState.FAILED
            return

        if not ctx.page:
            ctx.error = "No page available for self-heal"
            ctx.state = AgentState.FAILED
            return

        heal_attempts = getattr(ctx, "_heal_attempts", 0)
        if heal_attempts >= SELF_HEAL_MAX_RETRIES:
            ctx.error = f"Self-heal exhausted after {heal_attempts} attempts"
            ctx.state = AgentState.FAILED
            return

        logger.warning("[%s] Triggering self-heal attempt %d for %s",
                        ctx.job_id, heal_attempts + 1, ctx.scraper_name)

        from ecourts_scraper.agent.self_heal import attempt_self_heal

        site = self.scraper.get_source_site()
        error_msg = ctx.error or "Selector/locator failure"

        new_selector = attempt_self_heal(
            page=ctx.page,
            site=site,
            page_name=ctx.scraper_method,
            element_name="unknown",
            broken_selector={"by": "unknown", "value": "unknown"},
            error_message=error_msg,
        )

        ctx._heal_attempts = heal_attempts + 1

        if new_selector:
            logger.info("[%s] Self-heal suggested: %s, retrying from NAVIGATE", ctx.job_id, new_selector)
            ctx.state = AgentState.NAVIGATE
        else:
            ctx.error = f"Self-heal could not find replacement selector: {error_msg}"
            ctx.state = AgentState.FAILED

    def _handle_exception(self, ctx: AgentContext, exc: Exception):
        error_msg = str(exc).lower()

        if "timeout" in error_msg or "navigation" in error_msg:
            ctx.total_retries += 1
            if ctx.total_retries < MAX_AGENT_RETRIES:
                ctx.state = AgentState.BACKOFF
            else:
                ctx.error = f"Timeout after {ctx.total_retries} retries: {exc}"
                ctx.state = AgentState.FAILED

        elif "selector" in error_msg or "locator" in error_msg:
            ctx.state = AgentState.SELF_HEAL

        else:
            ctx.total_retries += 1
            if ctx.total_retries < MAX_AGENT_RETRIES:
                ctx.state = AgentState.BACKOFF
            else:
                ctx.error = f"Unrecoverable: {exc}"
                ctx.state = AgentState.FAILED

    def _cleanup_browser(self, ctx: AgentContext):
        if ctx.context:
            from ecourts_scraper.infra.browser_pool import browser_pool
            browser_pool.release_context(ctx.context)
            ctx.context = None
            ctx.page = None

    def cleanup(self, ctx: AgentContext):
        """Must be called in finally block after execute()."""
        self._cleanup_browser(ctx)
