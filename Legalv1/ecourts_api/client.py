"""
HTTP client for eCourts partner API (webapi.ecourtsindia.com).

Court-structure endpoints are FREE and require no auth.
All /api/partner/* endpoints require Bearer token and consume credits.
"""
import os
import logging
import hashlib
import json
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("django")

BASE_URL = "https://webapi.ecourtsindia.com"
TIMEOUT = 30  # seconds


def _get_token():
    return os.getenv("ECOURT_TOKEN", "")


def _session():
    """Build a requests.Session with retry logic."""
    s = requests.Session()
    retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


def _partner_headers():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/json",
    }


class EcourtsApiError(Exception):
    """Wraps errors from the eCourts external API."""

    def __init__(self, status_code, code, message, details=None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{status_code}] {code}: {message}")


def _handle_response(resp):
    """Parse response; raise EcourtsApiError on non-2xx."""
    if resp.ok:
        return resp.json()
    try:
        body = resp.json()
        err = body.get("error", {})
        raise EcourtsApiError(
            resp.status_code,
            err.get("code", "UNKNOWN"),
            err.get("message", resp.text),
            err.get("details"),
        )
    except (ValueError, KeyError):
        raise EcourtsApiError(resp.status_code, "UNKNOWN", resp.text)


# ── Partner (paid) endpoints ────────────────────────────────────────

def get_case(cnr: str) -> dict:
    """GET /api/partner/case/{cnr} — full case detail."""
    with _session() as s:
        resp = s.get(
            f"{BASE_URL}/api/partner/case/{cnr}",
            headers=_partner_headers(),
            timeout=TIMEOUT,
        )
    return _handle_response(resp)


def search(params: dict) -> dict:
    """
    GET /api/partner/search — full-text case search.
    `params` should be a dict of query params (advocates, litigants, judges,
    query, courtCodes, caseStatuses, page, pageSize, etc.)
    """
    with _session() as s:
        resp = s.get(
            f"{BASE_URL}/api/partner/search",
            headers=_partner_headers(),
            params=params,
            timeout=TIMEOUT,
        )
    return _handle_response(resp)


def get_causelist(params: dict) -> dict:
    """GET /api/partner/causelist/search — cause list search."""
    with _session() as s:
        resp = s.get(
            f"{BASE_URL}/api/partner/causelist/search",
            headers=_partner_headers(),
            params=params,
            timeout=TIMEOUT,
        )
    return _handle_response(resp)


def get_causelist_dates(params: dict) -> dict:
    """GET /api/partner/causelist/available-dates — FREE with auth."""
    with _session() as s:
        resp = s.get(
            f"{BASE_URL}/api/partner/causelist/available-dates",
            headers=_partner_headers(),
            params=params,
            timeout=TIMEOUT,
        )
    return _handle_response(resp)


def get_order(cnr: str, filename: str) -> dict:
    """GET /api/partner/case/{cnr}/order/{filename} — order PDF metadata."""
    with _session() as s:
        resp = s.get(
            f"{BASE_URL}/api/partner/case/{cnr}/order/{filename}",
            headers=_partner_headers(),
            timeout=TIMEOUT,
        )
    return _handle_response(resp)


def get_order_stream(cnr: str, filename: str):
    """
    Fetch order PDF from partner API and return (content_bytes, content_type).
    The eCourts partner API returns the PDF binary directly, NOT JSON, so we
    must NOT use _handle_response here (it would throw json.JSONDecodeError).
    Returns (bytes, str) tuple.
    """
    with _session() as s:
        resp = s.get(
            f"{BASE_URL}/api/partner/case/{cnr}/order/{filename}",
            headers=_partner_headers(),
            timeout=TIMEOUT,
        )
    if not resp.ok:
        try:
            body = resp.json()
            err = body.get("error", {})
            raise EcourtsApiError(
                resp.status_code,
                err.get("code", "UNKNOWN"),
                err.get("message", resp.text),
                err.get("details"),
            )
        except (ValueError, KeyError):
            raise EcourtsApiError(resp.status_code, "UNKNOWN", resp.text)
    content_type = resp.headers.get("Content-Type", "application/pdf")
    return resp.content, content_type


def refresh_case(cnr: str) -> dict:
    """POST /api/partner/case/{cnr}/refresh — queue fresh scrape."""
    with _session() as s:
        resp = s.post(
            f"{BASE_URL}/api/partner/case/{cnr}/refresh",
            headers=_partner_headers(),
            timeout=TIMEOUT,
        )
    return _handle_response(resp)


# ── Court structure (FREE, no auth) ────────────────────────────────

def get_states() -> list:
    """GET /api/CauseList/court-structure/states"""
    with _session() as s:
        resp = s.get(f"{BASE_URL}/api/CauseList/court-structure/states", timeout=TIMEOUT)
    return resp.json()  # returns raw list


def get_districts(state_code: str) -> list:
    """GET /api/CauseList/court-structure/states/{state}/districts"""
    with _session() as s:
        resp = s.get(
            f"{BASE_URL}/api/CauseList/court-structure/states/{state_code}/districts",
            timeout=TIMEOUT,
        )
    return resp.json()


def get_complexes(state_code: str, district_code: str) -> list:
    """GET /api/CauseList/court-structure/states/{state}/districts/{district}/complexes"""
    with _session() as s:
        resp = s.get(
            f"{BASE_URL}/api/CauseList/court-structure/states/{state_code}/districts/{district_code}/complexes",
            timeout=TIMEOUT,
        )
    return resp.json()


def get_courts(state_code: str, district_code: str, complex_code: str) -> list:
    """GET …/complexes/{code}/courts"""
    with _session() as s:
        resp = s.get(
            f"{BASE_URL}/api/CauseList/court-structure/states/{state_code}"
            f"/districts/{district_code}/complexes/{complex_code}/courts",
            timeout=TIMEOUT,
        )
    return resp.json()


# ── Cache-key helpers ───────────────────────────────────────────────

def make_search_cache_key(params: dict) -> str:
    """Deterministic cache key for search queries."""
    stable = json.dumps(params, sort_keys=True)
    h = hashlib.md5(stable.encode()).hexdigest()[:12]
    return f"api:search:{h}"


def make_causelist_cache_key(params: dict) -> str:
    stable = json.dumps(params, sort_keys=True)
    h = hashlib.md5(stable.encode()).hexdigest()[:12]
    return f"api:causelist:{h}"
