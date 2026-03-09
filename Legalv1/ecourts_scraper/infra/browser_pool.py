"""
Playwright browser pool manager.

Playwright's sync_api cannot run inside a gevent/asyncio event loop.
When the worker is gevent-patched (or forks from a gevent-patched parent),
we run each scrape in an isolated subprocess via `run_scraper_subprocess()`
rather than using the in-process pool.

For plain prefork workers with NO gevent patches, the in-process
BrowserPool (thread-safe) is used as normal.
"""
from __future__ import annotations

import threading
import logging
import random
import sys
from typing import TYPE_CHECKING, Any

from ecourts_scraper.constants import (
    MAX_CONCURRENT_BROWSERS,
    BROWSER_NAVIGATION_TIMEOUT_MS,
    USER_AGENTS,
)

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page

logger = logging.getLogger("django")


def _is_gevent_patched() -> bool:
    """Return True if gevent has monkey-patched this process."""
    try:
        from gevent import monkey
        return monkey.is_module_patched("socket")
    except ImportError:
        return False


class BrowserPool:
    """Thread-safe pool of Playwright browser contexts (in-process)."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._playwright = None
        self._browser: Any = None
        self._semaphore = threading.Semaphore(MAX_CONCURRENT_BROWSERS)
        self._init_lock = threading.Lock()

    def _ensure_browser(self):
        if self._browser and self._browser.is_connected():
            return
        with self._init_lock:
            if self._browser and self._browser.is_connected():
                return
            logger.info("Launching Playwright Chromium browser")
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-extensions",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-setuid-sandbox",
                ],
            )

    def acquire_context(self, proxy: dict | None = None) -> "BrowserContext":
        self._semaphore.acquire()
        try:
            self._ensure_browser()
            context_opts: dict = {
                "user_agent": random.choice(USER_AGENTS),
                "viewport": {"width": 1700, "height": 900},
                "ignore_https_errors": True,
                "java_script_enabled": True,
            }
            if proxy:
                context_opts["proxy"] = proxy
            context = self._browser.new_context(**context_opts)
            context.set_default_navigation_timeout(BROWSER_NAVIGATION_TIMEOUT_MS)
            context.set_default_timeout(BROWSER_NAVIGATION_TIMEOUT_MS)
            return context
        except Exception:
            self._semaphore.release()
            raise

    def release_context(self, context: "BrowserContext"):
        try:
            context.close()
        except Exception as e:
            logger.debug("Error closing browser context: %s", e)
        finally:
            self._semaphore.release()

    def new_page(self, context: "BrowserContext") -> "Page":
        return context.new_page()

    def shutdown(self):
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.debug("Error during browser pool shutdown: %s", e)


browser_pool = BrowserPool()


# ---------------------------------------------------------------------------
# Subprocess-based scraping (used when gevent is active)
# ---------------------------------------------------------------------------

_SUBPROCESS_RUNNER = """
import sys, json, os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Legalv1.settings")
import django
django.setup()

scraper_class_path = sys.argv[1]   # e.g. "ecourts_scraper.scrapers.highcourt.HighCourtScraper"
method = sys.argv[2]               # e.g. "case_by_cnr"
params = json.loads(sys.argv[3])   # JSON-encoded params dict

module_path, cls_name = scraper_class_path.rsplit(".", 1)
import importlib
mod = importlib.import_module(module_path)
scraper_cls = getattr(mod, cls_name)

from ecourts_scraper.infra.browser_pool import BrowserPool
pool = BrowserPool()
context = pool.acquire_context()
try:
    page = pool.new_page(context)
    scraper = scraper_cls()
    scraper.navigate(page, params)
    scraper.solve_captcha(page, 0)
    scraper.fill_form(page, params)
    result_state = scraper.submit_and_check(page)
    result = scraper.parse_results(page, params)
    print(json.dumps({"ok": True, "result": result}))
except Exception as e:
    import traceback
    print(json.dumps({"ok": False, "error": str(e), "tb": traceback.format_exc()}))
finally:
    pool.release_context(context)
"""


def run_scrape_in_subprocess(scraper_class_path: str, method: str, params: dict) -> dict:
    """
    Run a full scrape cycle in a clean subprocess to avoid gevent conflicts.
    Returns the parsed result dict or raises RuntimeError on failure.
    """
    import subprocess, json as _json

    result = subprocess.run(
        [sys.executable, "-c", _SUBPROCESS_RUNNER, scraper_class_path, method, _json.dumps(params)],
        capture_output=True,
        text=True,
        timeout=180,
    )

    stdout = result.stdout.strip()
    if result.returncode != 0 or not stdout:
        raise RuntimeError(
            f"Scraper subprocess failed (rc={result.returncode}):\n"
            f"stdout: {stdout}\nstderr: {result.stderr.strip()}"
        )

    try:
        data = _json.loads(stdout)
    except Exception:
        raise RuntimeError(f"Scraper subprocess returned non-JSON: {stdout[:500]}")

    if not data.get("ok"):
        raise RuntimeError(f"Scraper subprocess error: {data.get('error')}\n{data.get('tb','')}")

    return data["result"]
