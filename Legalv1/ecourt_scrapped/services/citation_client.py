"""
HTTP client for the FastAPI Supreme Court citation lookup scraper, mounted
at /sc on the same unified eCourts scraper process as the DC/HC clients.

All live (non-cached) calls go through this module. The scraper handles
sessions, CAPTCHA, and e-SCR portal interaction internally.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

SCRAPER_BASE = os.environ.get("SC_CITATION_SCRAPER_BASE_URL")
SCRAPER_TIMEOUT = int(os.environ.get("SC_CITATION_SCRAPER_TIMEOUT", "60"))


def _url(path: str) -> str:
    return f"{SCRAPER_BASE}/{path.lstrip('/')}"


def lookup_citation(citation: str, timeout: int | None = None) -> dict:
    """
    Resolve a citation string (or party-name/case-title free text) against
    the live e-SCR portal. Returns the parsed JSON body on success.

    Raises requests.HTTPError on a non-2xx response — callers decide how to
    translate that into a user-facing error (e.g. 404 = not found).
    """
    r = requests.post(
        _url("api/ecourts/v2/citations/lookup"),
        json={"citation": citation},
        timeout=timeout or SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def search_case_law(filters: dict, page: int = 1, page_size: int = 10, timeout: int | None = None) -> dict:
    """
    Run a filtered, paginated case-law search (first page of a new search —
    opens a session on the scraper side). Returns the parsed JSON body,
    including a `session_id` to pass to `search_case_law_page()` for
    subsequent pages without re-solving a captcha.
    """
    r = requests.post(
        _url("api/ecourts/v2/citations/case-search/search"),
        json={"filters": filters, "page": page, "page_size": page_size},
        timeout=timeout or SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def search_case_law_page(session_id: str, page: int, page_size: int = 10, timeout: int | None = None) -> dict:
    """Fetch a follow-up page of an existing case-law search session."""
    r = requests.post(
        _url("api/ecourts/v2/citations/case-search/page"),
        json={"session_id": session_id, "page": page, "page_size": page_size},
        timeout=timeout or SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def resolve_case_search_pdf(
    session_id: str, path: str, year: str, val: str, nc_display: str = "", timeout: int | None = None
) -> dict:
    """Resolve one case-search result row's PDF link on demand (click-to-resolve)."""
    r = requests.post(
        _url("api/ecourts/v2/citations/case-search/resolve"),
        json={"session_id": session_id, "path": path, "year": year, "val": val, "nc_display": nc_display},
        timeout=timeout or SCRAPER_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def health_check() -> dict:
    """Check if the FastAPI citation scraper is running."""
    try:
        r = requests.get(_url("health"), timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"SC citation scraper health check failed: {e}")
        return {"status": "unreachable", "error": str(e)}
