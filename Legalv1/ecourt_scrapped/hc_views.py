"""
Django views for the High Court eCourts scraper.

All views proxy requests to the HC FastAPI scraper (default: localhost:8001).
The HC scraper uses GET endpoints with query params — unlike the district-court
scraper which uses POST. Django views here accept JSON bodies from the frontend
and forward them as GET query params to the HC scraper.

Endpoints served under /api/ecourts/v2/hc/:
  GET  hc/health/
  GET  hc/courts/
  GET  hc/meta/police-stations/?hc=&bench=
  GET  hc/meta/court-numbers/?hc=&bench=
  GET  hc/case/cnr/<cino>/
  POST hc/case/party/
  POST hc/case/advocate/
  POST hc/case/bar-code/
  POST hc/case/filing/
  POST hc/case/fir/
  POST hc/orders/search/
  POST hc/orders/by-court/
  POST hc/orders/by-date/
  POST hc/causelist/
"""

import json
import logging
import traceback

from django.http import JsonResponse
from rest_framework.decorators import api_view

from supabase_required import supabase_required
from ecourt_scrapped.services import hc_scraper_client as hc

logger = logging.getLogger(__name__)


def _parse_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _error(msg, status=400):
    return JsonResponse({"error": msg}, status=status)


def _scraper_error_response(e):
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
# HEALTH / INFO
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@supabase_required
def hc_health(request):
    """GET /api/ecourts/v2/hc/health/"""
    return JsonResponse(hc.health_check())


@api_view(["GET"])
@supabase_required
def hc_courts(request):
    """
    GET /api/ecourts/v2/hc/courts/
    Returns all supported High Courts and their bench keys + labels.
    Response structure: { hc_slug: { name, benches: { bench_slug: label, ... } }, ... }
    """
    try:
        data = hc.get("courts")
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# METADATA
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@supabase_required
def hc_meta_police_stations(request):
    """
    GET /api/ecourts/v2/hc/meta/police-stations/?hc=<hc>&bench=<bench>
    Returns police station list for FIR search.
    """
    hc_key = request.GET.get("hc", "").strip()
    bench_key = request.GET.get("bench", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required query params")
    try:
        data = hc.get("meta/police_stations", params={"hc": hc_key, "bench": bench_key})
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["GET"])
@supabase_required
def hc_meta_court_numbers(request):
    """
    GET /api/ecourts/v2/hc/meta/court-numbers/?hc=<hc>&bench=<bench>
    Returns judge/court list for orders-by-court search.
    """
    hc_key = request.GET.get("hc", "").strip()
    bench_key = request.GET.get("bench", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required query params")
    try:
        data = hc.get("meta/court_numbers", params={"hc": hc_key, "bench": bench_key})
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# CASE LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@supabase_required
def hc_cnr_search(request, cino):
    """
    GET /api/ecourts/v2/hc/case/cnr/<cino>/
    HC and bench are auto-detected from the CNR prefix inside the HC scraper.
    Returns full HCCaseDetail.
    """
    cino = cino.strip().upper()
    if len(cino) < 10:
        return _error("Invalid CNR number")
    logger.info("hc_cnr_search: cino=%s", cino)
    try:
        data = hc.get(f"case/cnr/{cino}")
        logger.info("hc_cnr_search: success cino=%s high_court=%s", cino, data.get("high_court", "?") if isinstance(data, dict) else "?")
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error("hc_cnr_search: failed cino=%s error=%s", cino, e)
        return _scraper_error_response(e)


@api_view(["GET"])
@supabase_required
def hc_order_pdf(request):
    """
    GET /api/ecourts/v2/hc/order-pdf/?pdf_url=<url>
    Proxies an HC order PDF through the HC FastAPI scraper session.
    The HC portal requires a valid PHPSESSID cookie to serve display_pdf.php —
    the FastAPI scraper handles session creation and cookie injection.
    """
    from urllib.parse import urlparse
    from django.http import HttpResponse as _HR

    pdf_url = request.GET.get("pdf_url", "").strip()
    if not pdf_url:
        return _error("pdf_url is required")

    # SSRF guard — only allow HC portal URLs
    try:
        parsed_host = urlparse(pdf_url).hostname or ""
    except Exception:
        parsed_host = ""
    if parsed_host not in ("hcservices.ecourts.gov.in",):
        return _error("pdf_url must be from hcservices.ecourts.gov.in")

    logger.info("hc_order_pdf: fetching pdf_url=%s", pdf_url[:120])
    try:
        content, content_type = hc.get_binary("order-pdf", params={"pdf_url": pdf_url})
        resp = _HR(content, content_type="application/pdf")
        resp["Content-Disposition"] = 'inline; filename="order.pdf"'
        return resp
    except Exception as e:
        logger.error("hc_order_pdf: failed url=%s error=%s", pdf_url[:80], e)
        return _scraper_error_response(e)


@api_view(["GET"])
@supabase_required
def hc_causelist_pdf(request):
    """
    GET /api/ecourts/v2/hc/causelist-pdf/?pdf_url=<url>
    Proxies a causelist PDF (display_causelist_pdf.php) through the HC FastAPI
    scraper session — same session-cookie requirement as order PDFs.
    """
    from urllib.parse import urlparse
    from django.http import HttpResponse as _HR

    pdf_url = request.GET.get("pdf_url", "").strip()
    if not pdf_url:
        return _error("pdf_url is required")

    try:
        parsed_host = urlparse(pdf_url).hostname or ""
    except Exception:
        parsed_host = ""
    if parsed_host not in ("hcservices.ecourts.gov.in",):
        return _error("pdf_url must be from hcservices.ecourts.gov.in")

    logger.info("hc_causelist_pdf: fetching pdf_url=%s", pdf_url[:120])
    try:
        content, content_type = hc.get_binary("order-pdf", params={"pdf_url": pdf_url})
        resp = _HR(content, content_type="application/pdf")
        resp["Content-Disposition"] = 'inline; filename="causelist.pdf"'
        return resp
    except Exception as e:
        logger.error("hc_causelist_pdf: failed url=%s error=%s", pdf_url[:80], e)
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# CASE STATUS SEARCHES
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def hc_case_party(request):
    """
    POST /api/ecourts/v2/hc/case/party/
    Body: { hc, bench, name, year, status }
    Proxies to GET /case/party on HC scraper.
    """
    body = _parse_body(request)
    hc_key = body.get("hc", "").strip()
    bench_key = body.get("bench", "").strip()
    name = body.get("name", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required")
    if not name or len(name) < 3:
        return _error("name must be at least 3 characters")
    year = body.get("year", "").strip()
    if not year:
        return _error("year is required")
    params = {
        "hc": hc_key,
        "bench": bench_key,
        "name": name,
        "year": year,
    }
    status = body.get("status", "Both").strip()
    if status:
        params["status"] = status
    try:
        data = hc.get("case/party", params=params)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def hc_case_advocate(request):
    """
    POST /api/ecourts/v2/hc/case/advocate/
    Body: { hc, bench, query, status }
    """
    body = _parse_body(request)
    hc_key = body.get("hc", "").strip()
    bench_key = body.get("bench", "").strip()
    query = body.get("query", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required")
    if not query or len(query) < 3:
        return _error("query must be at least 3 characters")
    params = {"hc": hc_key, "bench": bench_key, "query": query}
    status = body.get("status", "Both").strip()
    if status:
        params["status"] = status
    try:
        data = hc.get("case/advocate", params=params)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def hc_case_bar_code(request):
    """
    POST /api/ecourts/v2/hc/case/bar-code/
    Body: { hc, bench, bar_code, status }
    """
    body = _parse_body(request)
    hc_key = body.get("hc", "").strip()
    bench_key = body.get("bench", "").strip()
    bar_code = body.get("bar_code", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required")
    if not bar_code:
        return _error("bar_code is required")
    params = {"hc": hc_key, "bench": bench_key, "bar_code": bar_code}
    status = body.get("status", "Both").strip()
    if status:
        params["status"] = status
    try:
        data = hc.get("case/bar-code", params=params)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def hc_case_filing(request):
    """
    POST /api/ecourts/v2/hc/case/filing/
    Body: { hc, bench, filing_number, year, case_type }
    """
    body = _parse_body(request)
    hc_key = body.get("hc", "").strip()
    bench_key = body.get("bench", "").strip()
    filing_number = body.get("filing_number", "").strip()
    year = body.get("year", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required")
    if not filing_number:
        return _error("filing_number is required")
    if not year:
        return _error("year is required")
    params = {
        "hc": hc_key,
        "bench": bench_key,
        "filing_number": filing_number,
        "year": year,
    }
    case_type = body.get("case_type", "").strip()
    if case_type:
        params["case_type"] = case_type
    try:
        data = hc.get("case/filing", params=params)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def hc_case_fir(request):
    """
    POST /api/ecourts/v2/hc/case/fir/
    Body: { hc, bench, police_station, status, fir_number, fir_year }
    """
    body = _parse_body(request)
    hc_key = body.get("hc", "").strip()
    bench_key = body.get("bench", "").strip()
    police_station = body.get("police_station", "").strip()
    status = body.get("status", "Both").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required")
    if not police_station:
        return _error("police_station is required")
    params = {
        "hc": hc_key,
        "bench": bench_key,
        "police_station": police_station,
        "status": status,
    }
    fir_number = body.get("fir_number", "").strip()
    fir_year = body.get("fir_year", "").strip()
    if fir_number:
        params["fir_number"] = fir_number
    if fir_year:
        params["fir_year"] = fir_year
    try:
        data = hc.get("case/fir", params=params)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# COURT ORDERS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def hc_orders_search(request):
    """
    POST /api/ecourts/v2/hc/orders/search/
    Body: { hc, bench, name, year }
    Proxies to GET /orders/search.
    """
    body = _parse_body(request)
    hc_key = body.get("hc", "").strip()
    bench_key = body.get("bench", "").strip()
    name = body.get("name", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required")
    if not name:
        return _error("name is required")
    params = {"hc": hc_key, "bench": bench_key, "name": name}
    year = body.get("year", "").strip()
    if year:
        params["year"] = year
    try:
        data = hc.get("orders/search", params=params)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def hc_orders_by_court(request):
    """
    POST /api/ecourts/v2/hc/orders/by-court/
    Body: { hc, bench, judge_code, date_from, date_to }
    Dates in YYYY-MM-DD format.
    """
    body = _parse_body(request)
    hc_key = body.get("hc", "").strip()
    bench_key = body.get("bench", "").strip()
    judge_code = body.get("judge_code", "").strip()
    date_from = body.get("date_from", "").strip()
    date_to = body.get("date_to", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required")
    if not judge_code:
        return _error("judge_code is required")
    if not date_from or not date_to:
        return _error("date_from and date_to are required (YYYY-MM-DD)")
    try:
        data = hc.get("orders/by-court", params={
            "hc": hc_key,
            "bench": bench_key,
            "judge_code": judge_code,
            "date_from": date_from,
            "date_to": date_to,
        })
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def hc_orders_by_date(request):
    """
    POST /api/ecourts/v2/hc/orders/by-date/
    Body: { hc, bench, date_from, date_to }
    Dates in DD-MM-YYYY format (different from by-court!).
    """
    body = _parse_body(request)
    hc_key = body.get("hc", "").strip()
    bench_key = body.get("bench", "").strip()
    date_from = body.get("date_from", "").strip()
    date_to = body.get("date_to", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required")
    if not date_from or not date_to:
        return _error("date_from and date_to are required (DD-MM-YYYY)")
    try:
        data = hc.get("orders/by-date", params={
            "hc": hc_key,
            "bench": bench_key,
            "date_from": date_from,
            "date_to": date_to,
        })
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# CAUSE LIST
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def hc_causelist(request):
    """
    POST /api/ecourts/v2/hc/causelist/
    Body: { hc, bench, list_date }
    list_date is optional (defaults to today inside scraper). Format: DD-MM-YYYY.
    """
    body = _parse_body(request)
    hc_key = body.get("hc", "").strip()
    bench_key = body.get("bench", "").strip()
    if not hc_key or not bench_key:
        return _error("hc and bench are required")
    params = {"hc": hc_key, "bench": bench_key}
    list_date = body.get("list_date", "").strip()
    if list_date:
        params["list_date"] = list_date
    try:
        data = hc.get("causelist", params=params)
        return JsonResponse(data, safe=False)
    except Exception as e:
        return _scraper_error_response(e)
