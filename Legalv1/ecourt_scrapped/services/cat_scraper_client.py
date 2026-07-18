"""
HTTP client for the FastAPI Central Administrative Tribunal (CAT) scraper.

All live calls go through this module. The scraper handles bench sessions
and CAT portal interaction internally — this client is a dumb proxy, same
pattern as sci_scraper_client.py. CAT has no CAPTCHA and returns direct PDF
URLs inline, so there is no post_pdf() helper here (unlike SCI/DC).
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

CAT_SCRAPER_BASE = os.environ.get("CAT_SCRAPER_BASE_URL")
CAT_SCRAPER_TIMEOUT = int(os.environ.get("CAT_SCRAPER_TIMEOUT", "60"))


def _url(path: str) -> str:
    return f"{CAT_SCRAPER_BASE}/{path.lstrip('/')}"


def get(endpoint: str, timeout: int | None = None) -> dict | list:
    """GET a scraper endpoint. Returns parsed JSON."""
    r = requests.get(_url(endpoint), timeout=timeout or CAT_SCRAPER_TIMEOUT)
    r.raise_for_status()
    return r.json()


def post(endpoint: str, payload: dict, timeout: int | None = None) -> dict | list:
    """POST JSON to a scraper endpoint. Returns parsed JSON."""
    r = requests.post(
        _url(endpoint),
        json=payload,
        timeout=timeout or CAT_SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def health_check() -> dict:
    """Check if the CAT FastAPI scraper is running."""
    try:
        return get("health", timeout=5)
    except Exception as e:
        logger.warning(f"CAT scraper health check failed: {e}")
        return {"status": "unreachable", "error": str(e)}
