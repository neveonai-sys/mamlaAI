"""
HTTP client for the FastAPI Supreme Court of India (SCI) scraper.

All live (non-cached) calls go through this module. The scraper handles
sessions, math-captcha solving, and SCI portal interaction internally —
this client is a dumb proxy, same pattern as scraper_client.py (DC).
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

SCI_SCRAPER_BASE = os.environ.get("SCI_SCRAPER_BASE_URL")
SCI_SCRAPER_TIMEOUT = int(os.environ.get("SCI_SCRAPER_TIMEOUT", "120"))


def _url(path: str) -> str:
    return f"{SCI_SCRAPER_BASE}/{path.lstrip('/')}"


def get(endpoint: str, params: dict | None = None, timeout: int | None = None) -> dict | list:
    """GET a scraper endpoint with optional query params. Returns parsed JSON."""
    r = requests.get(_url(endpoint), params=params, timeout=timeout or SCI_SCRAPER_TIMEOUT)
    r.raise_for_status()
    return r.json()


def post(endpoint: str, payload: dict, timeout: int | None = None) -> dict | list:
    """POST JSON to a scraper endpoint. Returns parsed JSON."""
    r = requests.post(
        _url(endpoint),
        json=payload,
        timeout=timeout or SCI_SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def post_pdf(endpoint: str, payload: dict, timeout: int | None = None) -> bytes:
    """POST to the document/pdf endpoint. Returns raw PDF bytes."""
    r = requests.post(
        _url(endpoint),
        json=payload,
        timeout=timeout or SCI_SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.content


def health_check() -> dict:
    """Check if the SCI FastAPI scraper is running."""
    try:
        return get("health", timeout=5)
    except Exception as e:
        logger.warning(f"SCI scraper health check failed: {e}")
        return {"status": "unreachable", "error": str(e)}
