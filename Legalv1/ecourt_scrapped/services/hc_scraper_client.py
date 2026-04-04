"""
HTTP client for the HC FastAPI scraper running on localhost:8001.

The HC scraper exposes GET-only endpoints — all params go as query strings.
Unlike the district-court scraper (POST-based), every call here uses requests.get().
"""

import logging
import os

import requests

logger = logging.getLogger("django")

HC_SCRAPER_BASE = os.environ.get("HC_SCRAPER_BASE_URL", "http://localhost:8001/hc")
HC_SCRAPER_TIMEOUT = int(os.environ.get("HC_SCRAPER_TIMEOUT", "120"))


def _url(path: str) -> str:
    return f"{HC_SCRAPER_BASE}/{path.lstrip('/')}"


def get(path: str, params: dict | None = None, timeout: int | None = None) -> dict | list:
    """GET an HC scraper endpoint with optional query params. Returns parsed JSON."""
    r = requests.get(
        _url(path),
        params=params,
        timeout=timeout or HC_SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def get_binary(path: str, params: dict | None = None, timeout: int | None = None) -> tuple:
    """GET an HC scraper endpoint and return (bytes, content_type). Used for PDF proxy."""
    r = requests.get(
        _url(path),
        params=params,
        timeout=timeout or HC_SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.content, r.headers.get("content-type", "application/pdf")


def health_check() -> dict:
    """Check if the HC FastAPI scraper is running."""
    try:
        return get("health", timeout=5)
    except Exception as e:
        logger.warning(f"HC scraper health check failed: {e}")
        return {"status": "unreachable", "error": str(e)}
