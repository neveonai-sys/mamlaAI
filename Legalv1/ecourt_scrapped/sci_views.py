"""
Django views for the Supreme Court of India (SCI) scraper.

Proxies all 5 flows to the SCI FastAPI scraper (mounted at /sci — see
scrapping_codes_ecourt/sci_fastapi_scrapper.py):
  Case Status   — case-number / diary-number / party-name / AOR-code
  Cause List    — today / tomorrow / by-date
  Daily Orders  — by-case / by-diary
  Judgments     — by-case / by-party / by-date
  Office Reports — by-case / by-diary

Plus shared case-types metadata and document/pdf streaming.

Endpoints served under /api/ecourts/v2/sci/:
  GET  sci/health/
  GET  sci/case-types/
  POST sci/case/by-number/ | by-diary/ | by-party/ | by-aor/
  GET  sci/causelist/today/ | tomorrow/
  POST sci/causelist/by-date/
  POST sci/orders/by-case/ | by-diary/
  POST sci/judgments/by-case/ | by-party/ | by-date/
  POST sci/office-report/by-case/ | by-diary/
  POST sci/document/pdf/
"""

import logging
import traceback

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view

from supabase_required import supabase_required
from ecourt_scrapped.services import sci_scraper_client as sci
from ecourt_scrapped.views import _parse_body, _error

logger = logging.getLogger(__name__)

CASE_TYPES_CACHE_KEY = "sci_case_types"
CASE_TYPES_CACHE_TTL = 60 * 60 * 24  # 24h — near-static list


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
def sci_health(request):
    """GET /api/ecourts/v2/sci/health/"""
    return JsonResponse(sci.health_check())


@api_view(["GET"])
@supabase_required
def sci_case_types(request):
    """GET /api/ecourts/v2/sci/case-types/ — cached 24h, near-static list."""
    cached = cache.get(CASE_TYPES_CACHE_KEY)
    if cached is not None:
        return JsonResponse(cached, safe=False)
    try:
        data = sci.get("case-types")
        cache.set(CASE_TYPES_CACHE_KEY, data, timeout=CASE_TYPES_CACHE_TTL)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# CASE STATUS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def sci_case_by_number(request):
    """POST /api/ecourts/v2/sci/case/by-number/ — Body: { case_type, case_no, case_year }"""
    body = _parse_body(request)
    required = ["case_type", "case_no", "case_year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = sci.post("case/by-number", {
            "case_type": body["case_type"],
            "case_no": body["case_no"],
            "case_year": body["case_year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def sci_case_by_diary(request):
    """POST /api/ecourts/v2/sci/case/by-diary/ — Body: { diary_no, diary_year }"""
    body = _parse_body(request)
    required = ["diary_no", "diary_year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = sci.post("case/by-diary", {
            "diary_no": body["diary_no"],
            "diary_year": body["diary_year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def sci_case_by_party(request):
    """POST /api/ecourts/v2/sci/case/by-party/ — Body: { party_name, year? }"""
    body = _parse_body(request)
    party_name = (body.get("party_name") or "").strip()
    if not party_name:
        return _error("party_name is required")
    payload = {"party_name": party_name}
    year = (body.get("year") or "").strip()
    if year:
        payload["year"] = year
    try:
        result = sci.post("case/by-party", payload)
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def sci_case_by_aor(request):
    """POST /api/ecourts/v2/sci/case/by-aor/ — Body: { aor_code, year? }"""
    body = _parse_body(request)
    aor_code = (body.get("aor_code") or "").strip()
    if not aor_code:
        return _error("aor_code is required")
    payload = {"aor_code": aor_code}
    year = (body.get("year") or "").strip()
    if year:
        payload["year"] = year
    try:
        result = sci.post("case/by-aor", payload)
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# CAUSE LIST
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@supabase_required
def sci_causelist_today(request):
    """GET /api/ecourts/v2/sci/causelist/today/"""
    try:
        return JsonResponse(sci.get("causelist/today"), safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["GET"])
@supabase_required
def sci_causelist_tomorrow(request):
    """GET /api/ecourts/v2/sci/causelist/tomorrow/"""
    try:
        return JsonResponse(sci.get("causelist/tomorrow"), safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def sci_causelist_by_date(request):
    """POST /api/ecourts/v2/sci/causelist/by-date/ — Body: { date } (DD-MM-YYYY)"""
    body = _parse_body(request)
    list_date = (body.get("date") or "").strip()
    if not list_date:
        return _error("date is required (DD-MM-YYYY)")
    try:
        result = sci.post("causelist/by-date", {"date": list_date})
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# DAILY ORDERS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def sci_orders_by_case(request):
    """POST /api/ecourts/v2/sci/orders/by-case/ — Body: { case_type, case_no, case_year }"""
    body = _parse_body(request)
    required = ["case_type", "case_no", "case_year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = sci.post("orders/by-case", {
            "case_type": body["case_type"],
            "case_no": body["case_no"],
            "case_year": body["case_year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def sci_orders_by_diary(request):
    """POST /api/ecourts/v2/sci/orders/by-diary/ — Body: { diary_no, diary_year }"""
    body = _parse_body(request)
    required = ["diary_no", "diary_year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = sci.post("orders/by-diary", {
            "diary_no": body["diary_no"],
            "diary_year": body["diary_year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# JUDGMENTS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def sci_judgments_by_case(request):
    """POST /api/ecourts/v2/sci/judgments/by-case/ — Body: { case_type, case_no, case_year }"""
    body = _parse_body(request)
    required = ["case_type", "case_no", "case_year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = sci.post("judgments/by-case", {
            "case_type": body["case_type"],
            "case_no": body["case_no"],
            "case_year": body["case_year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def sci_judgments_by_party(request):
    """POST /api/ecourts/v2/sci/judgments/by-party/ — Body: { party_name }"""
    body = _parse_body(request)
    party_name = (body.get("party_name") or "").strip()
    if not party_name:
        return _error("party_name is required")
    try:
        result = sci.post("judgments/by-party", {"party_name": party_name})
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def sci_judgments_by_date(request):
    """POST /api/ecourts/v2/sci/judgments/by-date/ — Body: { from_date, to_date } (DD-MM-YYYY)"""
    body = _parse_body(request)
    from_date = (body.get("from_date") or "").strip()
    to_date = (body.get("to_date") or "").strip()
    if not from_date or not to_date:
        return _error("from_date and to_date are required (DD-MM-YYYY)")
    try:
        result = sci.post("judgments/by-date", {"from_date": from_date, "to_date": to_date})
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# OFFICE REPORTS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def sci_office_report_by_case(request):
    """POST /api/ecourts/v2/sci/office-report/by-case/ — Body: { case_type, case_no, case_year }"""
    body = _parse_body(request)
    required = ["case_type", "case_no", "case_year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = sci.post("office-report/by-case", {
            "case_type": body["case_type"],
            "case_no": body["case_no"],
            "case_year": body["case_year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def sci_office_report_by_diary(request):
    """POST /api/ecourts/v2/sci/office-report/by-diary/ — Body: { diary_no, diary_year }"""
    body = _parse_body(request)
    required = ["diary_no", "diary_year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = sci.post("office-report/by-diary", {
            "diary_no": body["diary_no"],
            "diary_year": body["diary_year"],
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT / PDF
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def sci_document_pdf(request):
    """POST /api/ecourts/v2/sci/document/pdf/ — Body: { doc_url }"""
    body = _parse_body(request)
    doc_url = (body.get("doc_url") or "").strip()
    if not doc_url:
        return _error("doc_url is required")
    try:
        pdf_bytes = sci.post_pdf("document/pdf", {"doc_url": doc_url})
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="sci_document.pdf"'
        return response
    except Exception as e:
        return _scraper_error_response(e)
