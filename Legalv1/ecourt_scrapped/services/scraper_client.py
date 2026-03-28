"""
HTTP client for the FastAPI eCourts scraper running on localhost:3000.

All live (non-cached) calls go through this module.
The scraper handles sessions, CAPTCHA, and eCourts page interaction internally.
"""

import logging
import os

import requests

logger = logging.getLogger("django")

SCRAPER_BASE = os.environ.get("ECOURTS_SCRAPER_BASE_URL", "http://localhost:3000")
SCRAPER_TIMEOUT = int(os.environ.get("ECOURTS_SCRAPER_TIMEOUT", "120"))


def _url(path: str) -> str:
    return f"{SCRAPER_BASE}/{path.lstrip('/')}"


def get(endpoint: str, timeout: int | None = None) -> dict | list:
    """GET a scraper endpoint. Returns parsed JSON."""
    r = requests.get(_url(endpoint), timeout=timeout or SCRAPER_TIMEOUT)
    r.raise_for_status()
    return r.json()


def post(endpoint: str, payload: dict, timeout: int | None = None) -> dict | list:
    """POST JSON to a scraper endpoint. Returns parsed JSON."""
    r = requests.post(
        _url(endpoint),
        json=payload,
        timeout=timeout or SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def post_pdf(endpoint: str, payload: dict, timeout: int | None = None) -> bytes:
    """POST to the order-pdf endpoint. Returns raw PDF bytes."""
    r = requests.post(
        _url(endpoint),
        json=payload,
        timeout=timeout or SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.content


def health_check() -> dict:
    """Check if the FastAPI scraper is running."""
    try:
        return get("health", timeout=5)
    except Exception as e:
        logger.warning(f"eCourts scraper health check failed: {e}")
        return {"status": "unreachable", "error": str(e)}
