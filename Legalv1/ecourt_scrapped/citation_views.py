"""
Django views for Supreme Court citation lookup.

Proxies to the FastAPI SC citation scraper (mounted at /sc on the same
process as the DC/HC scrapers — see scrapping_codes_ecourt/main.py).

Owns what the FastAPI layer intentionally doesn't:
  - persistent caching (30 days — SC judgments are immutable once decided)
  - quota/entitlement enforcement (reuses the 'ecourts_case_lookup' feature
    bucket — this is another eCourts-family live-scrape lookup with the
    same CapSolver cost profile, so it shares that bucket rather than
    inventing new per-tier pricing for a brand-new feature code)
  - rate limiting
  - usage analytics

Endpoints served under /api/ecourts/v2/citations/:
  GET  citations/health/
  POST citations/lookup/
  POST citations/case-search/search/   (filtered, paginated "Search Case Law" — first page)
  POST citations/case-search/page/     (follow-up page of an existing search session)
  POST citations/case-search/resolve/  (resolve one result row's PDF link on demand)
"""

import hashlib
import json
import logging
import re
import traceback

from django.core.cache import cache
from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view

from supabase_required import supabase_required
from core.analytics import record_usage_event
from core.entitlements import authorize_feature_use, consume_feature_use
from ecourt_scrapped.services import citation_client

logger = logging.getLogger(__name__)

CITATION_FEATURE_CODE = 'ecourts_case_lookup'
CACHE_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days — judgments are immutable once decided


def _parse_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _cache_key(citation: str) -> str:
    normalized = re.sub(r"\s+", "", citation).upper()
    return "sc_citation:" + hashlib.sha256(normalized.encode()).hexdigest()


def _case_search_cache_key(filters: dict, page: int, page_size: int) -> str:
    normalized = json.dumps({"filters": filters, "page": page, "page_size": page_size}, sort_keys=True)
    return "sc_case_search:" + hashlib.sha256(normalized.encode()).hexdigest()


def _case_search_resolve_cache_key(path: str, year: str, val: str) -> str:
    # Keyed independent of session_id: the resolved PDF for a given
    # (path, year, val) is stable once a case is decided, so it can be
    # shared across different users' search sessions.
    normalized = json.dumps({"path": path, "year": year, "val": val}, sort_keys=True)
    return "sc_case_search_pdf:" + hashlib.sha256(normalized.encode()).hexdigest()


def _scraper_error_response(e):
    """Convert a requests.HTTPError from the scraper into a Django response."""
    import requests as req_lib
    if isinstance(e, req_lib.HTTPError) and e.response is not None:
        status = e.response.status_code
        try:
            detail = e.response.json()
        except Exception:
            detail = {"detail": e.response.text[:500]}
        return JsonResponse(detail, status=status)
    logger.error(traceback.format_exc())
    return JsonResponse({"error": str(e)}, status=502)


@api_view(["GET"])
@supabase_required
def citation_health(request):
    """GET /api/ecourts/v2/citations/health/"""
    return JsonResponse(citation_client.health_check())


@api_view(["POST"])
@supabase_required
@ratelimit(key='user', rate='20/m', block=True)
def citation_lookup(request):
    """
    POST /api/ecourts/v2/citations/lookup/
    Body: {"citation": "2024 INSC 45"}  (also accepts party-name/case-title free text)
    """
    body = _parse_body(request)
    citation = (body.get('citation') or '').strip()
    if not citation:
        return JsonResponse({'error': 'citation is required'}, status=400)

    supa_user = getattr(request, 'supabase_user', None)
    key = _cache_key(citation)

    cached = cache.get(key)
    if cached is not None:
        return JsonResponse({**cached, 'cached': True})

    decision = authorize_feature_use(supa_user, CITATION_FEATURE_CODE)
    if not decision.get('allowed'):
        return JsonResponse(
            {'error': decision['message'], 'quota': decision['quota']},
            status=decision.get('status_code', 429),
        )

    try:
        result = citation_client.lookup_citation(citation)
    except Exception as e:
        return _scraper_error_response(e)

    cache.set(key, result, timeout=CACHE_TTL_SECONDS)
    quota = consume_feature_use(supa_user, CITATION_FEATURE_CODE, decision)
    record_usage_event(
        request,
        feature='citation_lookup',
        model='e-scr',
        prompt_tokens=0,
        completion_tokens=0,
        metadata={'citation': citation, 'resolved_target': result.get('resolved_target')},
    )

    return JsonResponse({**result, 'cached': False, 'quota': quota})


@api_view(["POST"])
@supabase_required
@ratelimit(key='user', rate='20/m', block=True)
def citation_case_search(request):
    """
    POST /api/ecourts/v2/citations/case-search/search/
    Body: {"filters": {...}, "page": 1, "page_size": 10}

    First page of a new filtered case-law search — opens a session on the
    scraper side (see scrapping_codes_ecourt/sc_citation_scraper.py). The
    response's `session_id` should be passed to case-search/page/ for
    subsequent pages, which are cheap (no captcha re-solve) on the scraper
    side and are not separately cached here.
    """
    body = _parse_body(request)
    filters = body.get('filters') or {}
    page = int(body.get('page') or 1)
    page_size = int(body.get('page_size') or 10)

    supa_user = getattr(request, 'supabase_user', None)
    key = _case_search_cache_key(filters, page, page_size)

    cached = cache.get(key)
    if cached is not None:
        return JsonResponse({**cached, 'cached': True})

    decision = authorize_feature_use(supa_user, CITATION_FEATURE_CODE)
    if not decision.get('allowed'):
        return JsonResponse(
            {'error': decision['message'], 'quota': decision['quota']},
            status=decision.get('status_code', 429),
        )

    try:
        result = citation_client.search_case_law(filters, page=page, page_size=page_size)
    except Exception as e:
        return _scraper_error_response(e)

    cache.set(key, result, timeout=CACHE_TTL_SECONDS)
    quota = consume_feature_use(supa_user, CITATION_FEATURE_CODE, decision)
    record_usage_event(
        request,
        feature='citation_case_search',
        model='e-scr',
        prompt_tokens=0,
        completion_tokens=0,
        metadata={'filters': filters, 'page': page},
    )

    return JsonResponse({**result, 'cached': False, 'quota': quota})


@api_view(["POST"])
@supabase_required
@ratelimit(key='user', rate='60/m', block=True)
def citation_case_search_resolve(request):
    """
    POST /api/ecourts/v2/citations/case-search/resolve/
    Body: {"session_id": "...", "path": "...", "year": "...", "val": "...", "nc_display": "..."}

    Resolves one result row's PDF link on demand (click-to-resolve, mirrors
    the real portal's PDF button). Cached independent of session_id since a
    decided case's PDF is stable — a repeat click (by the same or a
    different user) doesn't need to hit the live portal or a session again.
    """
    body = _parse_body(request)
    session_id = (body.get('session_id') or '').strip()
    path = (body.get('path') or '').strip()
    year = (body.get('year') or '').strip()
    val = (body.get('val') or '').strip()
    nc_display = (body.get('nc_display') or '').strip()
    if not session_id or not path or not year or not val:
        return JsonResponse({'error': 'session_id, path, year, and val are required'}, status=400)

    supa_user = getattr(request, 'supabase_user', None)
    key = _case_search_resolve_cache_key(path, year, val)

    cached = cache.get(key)
    if cached is not None:
        return JsonResponse({**cached, 'cached': True})

    decision = authorize_feature_use(supa_user, CITATION_FEATURE_CODE)
    if not decision.get('allowed'):
        return JsonResponse(
            {'error': decision['message'], 'quota': decision['quota']},
            status=decision.get('status_code', 429),
        )

    try:
        result = citation_client.resolve_case_search_pdf(session_id, path, year, val, nc_display)
    except Exception as e:
        return _scraper_error_response(e)

    if result.get('pdf_url'):
        cache.set(key, result, timeout=CACHE_TTL_SECONDS)
    quota = consume_feature_use(supa_user, CITATION_FEATURE_CODE, decision)
    record_usage_event(
        request,
        feature='citation_case_search',
        model='e-scr',
        prompt_tokens=0,
        completion_tokens=0,
        metadata={'path': path, 'year': year, 'val': val},
    )

    return JsonResponse({**result, 'cached': False, 'quota': quota})


@api_view(["POST"])
@supabase_required
@ratelimit(key='user', rate='40/m', block=True)
def citation_case_search_page(request):
    """
    POST /api/ecourts/v2/citations/case-search/page/
    Body: {"session_id": "...", "page": 2, "page_size": 10}

    Follow-up page of an existing search session. Not cached here — the
    scraper-side session already makes this cheap (no captcha re-solve),
    and a session_id is single-use/ephemeral so a cache entry keyed on it
    would never hit again.
    """
    body = _parse_body(request)
    session_id = (body.get('session_id') or '').strip()
    if not session_id:
        return JsonResponse({'error': 'session_id is required'}, status=400)
    page = int(body.get('page') or 1)
    page_size = int(body.get('page_size') or 10)

    supa_user = getattr(request, 'supabase_user', None)
    decision = authorize_feature_use(supa_user, CITATION_FEATURE_CODE)
    if not decision.get('allowed'):
        return JsonResponse(
            {'error': decision['message'], 'quota': decision['quota']},
            status=decision.get('status_code', 429),
        )

    try:
        result = citation_client.search_case_law_page(session_id, page=page, page_size=page_size)
    except Exception as e:
        return _scraper_error_response(e)

    quota = consume_feature_use(supa_user, CITATION_FEATURE_CODE, decision)
    record_usage_event(
        request,
        feature='citation_case_search',
        model='e-scr',
        prompt_tokens=0,
        completion_tokens=0,
        metadata={'session_id': session_id, 'page': page},
    )

    return JsonResponse({**result, 'cached': False, 'quota': quota})
