"""
Django views for the Central Administrative Tribunal (CAT) scraper.

Proxies all flows to the CAT FastAPI scraper (mounted at /cat — see
scrapping_codes_ecourt/cat_fastapi_scrapper.py):
  Case Status   — case-number / diary-number / party-name / advocate-name,
                  plus the case/detail drilldown from a search result's token
  Cause List    — by bench + date
  Orders        — daily (5 modes) / final (4 modes)
  Judgments     — full-text keyword search (unverified, see scraper module docstring)

Plus shared benches / case-types / judges metadata (all cached 24h — near-static).

CAT has no CAPTCHA and returns direct, stable PDF URLs inline in the JSON —
there is no document/pdf streaming view here (unlike DC/SCI).

Endpoints served under /api/ecourts/v2/cat/:
  GET  cat/health/ | benches/ | case-types/ | judges/
  POST cat/case/by-number/ | by-diary/ | by-party/ | by-advocate/ | detail/
  POST cat/causelist/
  POST cat/orders/daily/by-case/ | by-diary/ | by-party/ | by-date/ | by-judge/
  POST cat/orders/final/by-case/ | by-diary/ | by-date/ | by-judge/
  POST cat/judgments/search/
"""

import logging
import traceback

from django.core.cache import cache
from django.http import JsonResponse
from rest_framework.decorators import api_view

from supabase_required import supabase_required
from ecourt_scrapped.services import cat_scraper_client as cat
from ecourt_scrapped.views import _parse_body, _error

logger = logging.getLogger(__name__)

BENCHES_CACHE_KEY = "cat_benches"
CASE_TYPES_CACHE_KEY = "cat_case_types"
JUDGES_CACHE_KEY = "cat_judges"
REFERENCE_CACHE_TTL = 60 * 60 * 24  # 24h — near-static lists


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


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH / METADATA
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@supabase_required
def cat_health(request):
    """GET /api/ecourts/v2/cat/health/"""
    return JsonResponse(cat.health_check())


@api_view(["GET"])
@supabase_required
def cat_benches(request):
    """GET /api/ecourts/v2/cat/benches/ — cached 24h, static list of 19 benches."""
    cached = cache.get(BENCHES_CACHE_KEY)
    if cached is not None:
        return JsonResponse(cached, safe=False)
    try:
        data = cat.get("benches")
        cache.set(BENCHES_CACHE_KEY, data, timeout=REFERENCE_CACHE_TTL)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["GET"])
@supabase_required
def cat_case_types(request):
    """GET /api/ecourts/v2/cat/case-types/ — cached 24h, near-static list."""
    cached = cache.get(CASE_TYPES_CACHE_KEY)
    if cached is not None:
        return JsonResponse(cached, safe=False)
    try:
        data = cat.get("case-types")
        cache.set(CASE_TYPES_CACHE_KEY, data, timeout=REFERENCE_CACHE_TTL)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["GET"])
@supabase_required
def cat_judges(request):
    """GET /api/ecourts/v2/cat/judges/ — cached 24h. Used by the
    orders-by-judge modes. Only caches a non-trivial list — the live site
    intermittently 500s and serves a placeholder-only judge dropdown, and an
    empty response shouldn't get stuck in cache for 24h."""
    cached = cache.get(JUDGES_CACHE_KEY)
    if cached is not None:
        return JsonResponse(cached, safe=False)
    try:
        data = cat.get("judges")
        if isinstance(data, list) and len(data) > 10:
            cache.set(JUDGES_CACHE_KEY, data, timeout=REFERENCE_CACHE_TTL)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# CASE STATUS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def cat_case_by_number(request):
    """POST /api/ecourts/v2/cat/case/by-number/ — Body: { bench, case_type, case_no, year }"""
    body = _parse_body(request)
    required = ["bench", "case_type", "case_no", "year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = cat.post("case/by-number", {
            "bench": body["bench"],
            "case_type": body["case_type"],
            "case_no": body["case_no"],
            "year": body["year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def cat_case_by_diary(request):
    """POST /api/ecourts/v2/cat/case/by-diary/ — Body: { bench, diary_no, year }"""
    body = _parse_body(request)
    required = ["bench", "diary_no", "year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = cat.post("case/by-diary", {
            "bench": body["bench"],
            "diary_no": body["diary_no"],
            "year": body["year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def cat_case_by_party(request):
    """POST /api/ecourts/v2/cat/case/by-party/ — Body: { bench, party_name, party_type? }"""
    body = _parse_body(request)
    bench = (body.get("bench") or "").strip()
    party_name = (body.get("party_name") or "").strip()
    if not bench or not party_name:
        return _error("bench and party_name are required")
    try:
        result = cat.post("case/by-party", {
            "bench": bench,
            "party_name": party_name,
            "party_type": body.get("party_type", "Both"),
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def cat_case_by_advocate(request):
    """POST /api/ecourts/v2/cat/case/by-advocate/ — Body: { bench, advocate_name, advocate_type? }"""
    body = _parse_body(request)
    bench = (body.get("bench") or "").strip()
    advocate_name = (body.get("advocate_name") or "").strip()
    if not bench or not advocate_name:
        return _error("bench and advocate_name are required")
    try:
        result = cat.post("case/by-advocate", {
            "bench": bench,
            "advocate_name": advocate_name,
            "advocate_type": body.get("advocate_type", "Petitioner"),
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def cat_case_detail(request):
    """POST /api/ecourts/v2/cat/case/detail/ — Body: { token }
    token comes from a Case Status search result's detail_token field."""
    body = _parse_body(request)
    token = (body.get("token") or "").strip()
    if not token:
        return _error("token is required")
    try:
        result = cat.post("case/detail", {"token": token})
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# CAUSE LIST
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def cat_causelist(request):
    """POST /api/ecourts/v2/cat/causelist/ — Body: { bench, date } (dd-mm-yyyy)"""
    body = _parse_body(request)
    bench = (body.get("bench") or "").strip()
    date = (body.get("date") or "").strip()
    if not bench or not date:
        return _error("bench and date are required (dd-mm-yyyy)")
    try:
        result = cat.post("causelist", {"bench": bench, "date": date})
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# ORDERS — Daily (5 modes) / Final (4 modes)
# ─────────────────────────────────────────────────────────────────────────────

def _orders_by_case(request, scraper_endpoint):
    body = _parse_body(request)
    required = ["bench", "case_type", "case_no", "year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = cat.post(scraper_endpoint, {
            "bench": body["bench"], "case_type": body["case_type"],
            "case_no": body["case_no"], "year": body["year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


def _orders_by_diary(request, scraper_endpoint):
    body = _parse_body(request)
    required = ["bench", "diary_no", "year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = cat.post(scraper_endpoint, {
            "bench": body["bench"], "diary_no": body["diary_no"], "year": body["year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


def _orders_by_date(request, scraper_endpoint):
    body = _parse_body(request)
    required = ["bench", "from_date", "to_date"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing} (dd-mm-yyyy)")
    try:
        result = cat.post(scraper_endpoint, {
            "bench": body["bench"], "from_date": body["from_date"], "to_date": body["to_date"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


def _orders_by_judge(request, scraper_endpoint):
    body = _parse_body(request)
    bench = (body.get("bench") or "").strip()
    judge_code = (body.get("judge_code") or "").strip()
    if not bench or not judge_code:
        return _error("bench and judge_code are required")
    try:
        result = cat.post(scraper_endpoint, {"bench": bench, "judge_code": judge_code})
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def cat_orders_daily_by_case(request):
    """POST /api/ecourts/v2/cat/orders/daily/by-case/ — Body: { bench, case_type, case_no, year }"""
    return _orders_by_case(request, "orders/daily/by-case")


@api_view(["POST"])
@supabase_required
def cat_orders_daily_by_diary(request):
    """POST /api/ecourts/v2/cat/orders/daily/by-diary/ — Body: { bench, diary_no, year }"""
    return _orders_by_diary(request, "orders/daily/by-diary")


@api_view(["POST"])
@supabase_required
def cat_orders_daily_by_party(request):
    """POST /api/ecourts/v2/cat/orders/daily/by-party/ — Body: { bench, party_name, party_type? }"""
    body = _parse_body(request)
    bench = (body.get("bench") or "").strip()
    party_name = (body.get("party_name") or "").strip()
    if not bench or not party_name:
        return _error("bench and party_name are required")
    try:
        result = cat.post("orders/daily/by-party", {
            "bench": bench, "party_name": party_name, "party_type": body.get("party_type", "Both"),
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def cat_orders_daily_by_date(request):
    """POST /api/ecourts/v2/cat/orders/daily/by-date/ — Body: { bench, from_date, to_date } (dd-mm-yyyy)"""
    return _orders_by_date(request, "orders/daily/by-date")


@api_view(["POST"])
@supabase_required
def cat_orders_daily_by_judge(request):
    """POST /api/ecourts/v2/cat/orders/daily/by-judge/ — Body: { bench, judge_code }"""
    return _orders_by_judge(request, "orders/daily/by-judge")


@api_view(["POST"])
@supabase_required
def cat_orders_final_by_case(request):
    """POST /api/ecourts/v2/cat/orders/final/by-case/ — Body: { bench, case_type, case_no, year }"""
    return _orders_by_case(request, "orders/final/by-case")


@api_view(["POST"])
@supabase_required
def cat_orders_final_by_diary(request):
    """POST /api/ecourts/v2/cat/orders/final/by-diary/ — Body: { bench, diary_no, year }"""
    return _orders_by_diary(request, "orders/final/by-diary")


@api_view(["POST"])
@supabase_required
def cat_orders_final_by_date(request):
    """POST /api/ecourts/v2/cat/orders/final/by-date/ — Body: { bench, from_date, to_date } (dd-mm-yyyy)"""
    return _orders_by_date(request, "orders/final/by-date")


@api_view(["POST"])
@supabase_required
def cat_orders_final_by_judge(request):
    """POST /api/ecourts/v2/cat/orders/final/by-judge/ — Body: { bench, judge_code }"""
    return _orders_by_judge(request, "orders/final/by-judge")


# ─────────────────────────────────────────────────────────────────────────────
# JUDGMENTS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def cat_judgments_search(request):
    """POST /api/ecourts/v2/cat/judgments/search/ — Body: { bench?, query, from_year?, to_year? }"""
    body = _parse_body(request)
    query = (body.get("query") or "").strip()
    if not query:
        return _error("query is required")
    try:
        result = cat.post("judgments/search", {
            "bench": body.get("bench", "all"),
            "query": query,
            "from_year": body.get("from_year", "2020"),
            "to_year": body.get("to_year", ""),
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)
