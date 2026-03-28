"""
Django views for the eCourt Scrapped app.

Proxies all 4 flows to the FastAPI scraper (localhost:3000):
  A — Direct lookup (CNR / CINO)
  B — Cause list cascade + fetch
  C — Case status search (party, filing, advocate, FIR)
  D — Court orders search (party, case number, court number, date)

Plus shared resolvers (case/from-url, case/history, case/order-pdf)
and cached dropdown endpoints.
"""

import json
import logging
import traceback

from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view

from supabase_required import supabase_required
from ecourt_scrapped.services import master_data, scraper_client

logger = logging.getLogger("django")


def _parse_body(request):
    """Parse JSON body from request, return empty dict on failure."""
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _error(msg, status=400):
    return JsonResponse({"error": msg}, status=status)


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
# HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@supabase_required
def scraper_health(request):
    """GET /api/ecourts/health/ — check FastAPI scraper connectivity."""
    return JsonResponse(scraper_client.health_check())


# ─────────────────────────────────────────────────────────────────────────────
# DROPDOWN / MASTER DATA  (cached in MongoDB)
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@supabase_required
def get_states(request):
    """GET /api/ecourts/states/"""
    try:
        return JsonResponse(master_data.get_states(), safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def get_districts(request):
    """POST /api/ecourts/districts/"""
    body = _parse_body(request)
    state_code = body.get("state_code", "")
    if not state_code:
        return _error("state_code is required")
    try:
        return JsonResponse(master_data.get_districts(state_code), safe=False)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def get_complexes(request):
    """POST /api/ecourts/complexes/"""
    body = _parse_body(request)
    state_code = body.get("state_code", "")
    dist_code = body.get("dist_code", "")
    if not state_code or not dist_code:
        return _error("state_code and dist_code are required")
    try:
        return JsonResponse(
            master_data.get_complexes(state_code, dist_code), safe=False
        )
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def get_establishments(request):
    """POST /api/ecourts/establishments/"""
    body = _parse_body(request)
    state_code = body.get("state_code", "")
    dist_code = body.get("dist_code", "")
    court_complex_code = body.get("court_complex_code", "")
    if not all([state_code, dist_code, court_complex_code]):
        return _error("state_code, dist_code, and court_complex_code are required")
    try:
        return JsonResponse(
            master_data.get_establishments(state_code, dist_code, court_complex_code),
            safe=False,
        )
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def get_courts(request):
    """POST /api/ecourts/courts/"""
    body = _parse_body(request)
    state_code = body.get("state_code", "")
    dist_code = body.get("dist_code", "")
    court_complex_code = body.get("court_complex_code", "")
    est_code = body.get("est_code", "")
    if not all([state_code, dist_code, court_complex_code, est_code]):
        return _error("state_code, dist_code, court_complex_code, and est_code are required")
    try:
        return JsonResponse(
            master_data.get_courts(state_code, dist_code, court_complex_code, est_code),
            safe=False,
        )
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def get_police_stations(request):
    """POST /api/ecourts/police-stations/"""
    body = _parse_body(request)
    state_code = body.get("state_code", "")
    dist_code = body.get("dist_code", "")
    court_complex_code = body.get("court_complex_code", "")
    est_code = body.get("est_code", "")
    if not all([state_code, dist_code, court_complex_code, est_code]):
        return _error("state_code, dist_code, court_complex_code, and est_code are required")
    try:
        return JsonResponse(
            master_data.get_police_stations(state_code, dist_code, court_complex_code, est_code),
            safe=False,
        )
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def get_order_case_types(request):
    """POST /api/ecourts/order-case-types/"""
    body = _parse_body(request)
    state_code = body.get("state_code", "")
    dist_code = body.get("dist_code", "")
    court_complex_code = body.get("court_complex_code", "")
    est_code = body.get("est_code", "")
    if not all([state_code, dist_code, court_complex_code, est_code]):
        return _error("state_code, dist_code, court_complex_code, and est_code are required")
    try:
        return JsonResponse(
            master_data.get_order_case_types(state_code, dist_code, court_complex_code, est_code),
            safe=False,
        )
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def get_order_court_numbers(request):
    """POST /api/ecourts/order-court-numbers/"""
    body = _parse_body(request)
    state_code = body.get("state_code", "")
    dist_code = body.get("dist_code", "")
    court_complex_code = body.get("court_complex_code", "")
    est_code = body.get("est_code", "")  # optional — complex-level lookup works without it
    if not all([state_code, dist_code, court_complex_code]):
        return _error("state_code, dist_code, and court_complex_code are required")
    try:
        # Use FastAPI courtorder/court-numbers directly — it calls courtorder/fillCourtNumber
        # which returns codes in the correct "est$court^from^to" format needed by by-court-number.
        # master_data._scrape_live used scrape_courts (causelist fillCourt) which returns a
        # different code format ("2^8") that breaks the court number search payload.
        result = scraper_client.post("courtorder/court-numbers", {
            "state_code":         state_code,
            "dist_code":          dist_code,
            "court_complex_code": court_complex_code,
            "est_code":           est_code,
        })
        return JsonResponse(result, safe=False)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# FLOW A — DIRECT CASE LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def cnr_search(request):
    """POST /api/ecourts/cnr/search/ — search case by CNR number."""
    body = _parse_body(request)
    cnr_number = (body.get("cnr_number") or "").strip().upper()
    if not cnr_number or len(cnr_number) != 16 or not cnr_number.isalnum():
        return _error("cnr_number must be exactly 16 alphanumeric characters")
    try:
        result = scraper_client.post("cnr/search", {"cnr_number": cnr_number})
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def case_by_cino(request):
    """POST /api/ecourts/case/by-cino/ — search case by CINO."""
    body = _parse_body(request)
    cino = (body.get("cino") or "").strip().upper()
    if not cino:
        return _error("cino is required")
    try:
        result = scraper_client.post("case/by-cino", {"cino": cino})
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED RESOLVERS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def case_from_url(request):
    """POST /api/ecourts/case/from-url/ — resolve case detail from view_history_url."""
    body = _parse_body(request)
    url = body.get("view_history_url", "")
    if not url:
        return _error("view_history_url is required")
    try:
        result = scraper_client.post("case/from-url", {"view_history_url": url})
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def case_history(request):
    """POST /api/ecourts/case/history/ — resolve case detail from individual fields."""
    body = _parse_body(request)
    required = ["case_no", "cino", "court_code", "state_code", "dist_code", "court_complex_code"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = scraper_client.post("case/history", {
            "case_no": body["case_no"],
            "cino": body["cino"],
            "court_code": body["court_code"],
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
        })
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def case_detail(request):
    """
    POST /api/ecourts/case/detail/ — unified case detail resolver.
    Accepts view_history_url, cino, or cnr_number (tries in that order).
    """
    body = _parse_body(request)
    try:
        if body.get("view_history_url"):
            result = scraper_client.post("case/from-url", {
                "view_history_url": body["view_history_url"],
            })
        elif body.get("cino"):
            result = scraper_client.post("case/by-cino", {
                "cino": body["cino"].strip().upper(),
            })
        elif body.get("cnr_number"):
            result = scraper_client.post("cnr/search", {
                "cnr_number": body["cnr_number"].strip().upper(),
            })
        else:
            return _error("Provide view_history_url, cino, or cnr_number")
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def order_pdf(request):
    """POST /api/ecourts/case/order-pdf/ — download court order PDF."""
    body = _parse_body(request)
    required = ["normal_v", "case_val", "court_code", "filename"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required pdf_params fields: {missing}")
    try:
        pdf_bytes = scraper_client.post_pdf("case/order-pdf", {
            "normal_v": body["normal_v"],
            "case_val": body["case_val"],
            "court_code": body["court_code"],
            "filename": body["filename"],
        })
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="court_order.pdf"'
        return response
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# FLOW B — CAUSE LIST
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def causelist_fetch(request):
    """POST /api/ecourts/causelist/fetch/ — fetch cause list for a specific court+date."""
    body = _parse_body(request)
    required = [
        "state_code", "dist_code", "court_complex_code",
        "est_code", "court_no", "court_name", "date", "list_type",
    ]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    list_type = body["list_type"].lower()
    if list_type not in ("civil", "criminal"):
        return _error("list_type must be 'civil' or 'criminal'")
    try:
        result = scraper_client.post("causelist/fetch", {
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
            "est_code": body["est_code"],
            "court_no": body["court_no"],
            "court_name": body["court_name"],
            "date": body["date"],
            "list_type": list_type,
        })
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# FLOW C — CASE STATUS SEARCH
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def casestatus_by_party(request):
    """POST /api/ecourts/casestatus/by-party/"""
    body = _parse_body(request)
    required = ["state_code", "dist_code", "court_complex_code", "est_code", "party_name"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = scraper_client.post("casestatus/by-party", {
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
            "est_code": body["est_code"],
            "party_name": body["party_name"],
            "registration_year": body.get("registration_year", ""),
            "case_status": body.get("case_status", "Pending"),
        })
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def casestatus_by_filing(request):
    """POST /api/ecourts/casestatus/by-filing/"""
    body = _parse_body(request)
    required = ["state_code", "dist_code", "court_complex_code", "est_code",
                "filing_number", "filing_year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = scraper_client.post("casestatus/by-filing", {
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
            "est_code": body["est_code"],
            "filing_number": body["filing_number"],
            "filing_year": body["filing_year"],
        })
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def casestatus_by_advocate(request):
    """POST /api/ecourts/casestatus/by-advocate/"""
    body = _parse_body(request)
    required = ["state_code", "dist_code", "court_complex_code", "est_code", "search_by"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")

    search_by = body["search_by"]
    if search_by == "name" and not body.get("advocate_name"):
        return _error("advocate_name is required when search_by='name'")
    if search_by in ("code", "date_caselist") and not body.get("advocate_code"):
        return _error("advocate_code is required for this search mode")
    if search_by == "date_caselist" and not body.get("caselist_date"):
        return _error("caselist_date is required when search_by='date_caselist'")

    try:
        payload = {
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
            "est_code": body["est_code"],
            "search_by": search_by,
            "advocate_name": body.get("advocate_name", ""),
            "advocate_state_code": body.get("advocate_state_code", ""),
            "advocate_code": body.get("advocate_code", ""),
            "advocate_year": body.get("advocate_year", ""),
            "caselist_date": body.get("caselist_date", ""),
            "case_status": body.get("case_status", "Pending"),
        }
        result = scraper_client.post("casestatus/by-advocate", payload)
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def casestatus_by_fir(request):
    """POST /api/ecourts/casestatus/by-fir/"""
    body = _parse_body(request)
    required = ["state_code", "dist_code", "court_complex_code", "est_code",
                "police_station_code"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = scraper_client.post("casestatus/by-fir", {
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
            "est_code": body["est_code"],
            "police_station_code": body["police_station_code"],
            "ps_state_code": body.get("ps_state_code", ""),
            "ps_uniform_code": body.get("ps_uniform_code", ""),
            "fir_number": body.get("fir_number", ""),
            "fir_year": body.get("fir_year", ""),
            "case_status": body.get("case_status", "Both"),
        })
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# FLOW D — COURT ORDERS SEARCH
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def courtorder_by_party(request):
    """POST /api/ecourts/courtorder/by-party/"""
    body = _parse_body(request)
    required = ["state_code", "dist_code", "court_complex_code", "party_name", "year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = scraper_client.post("courtorder/by-party", {
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
            "est_code": body.get("est_code", ""),
            "party_name": body["party_name"],
            "year": body["year"],
            "order_type": body.get("order_type", "both"),
        })
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def courtorder_by_case_number(request):
    """POST /api/ecourts/courtorder/by-case-number/"""
    body = _parse_body(request)
    required = ["state_code", "dist_code", "court_complex_code",
                "case_type", "case_number", "year"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = scraper_client.post("courtorder/by-case-number", {
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
            "est_code": body.get("est_code", ""),
            "case_type": body["case_type"],
            "case_number": body["case_number"],
            "year": body["year"],
            "order_type": body.get("order_type", "both"),
        })
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def courtorder_by_court_number(request):
    """POST /api/ecourts/courtorder/by-court-number/"""
    body = _parse_body(request)
    required = ["state_code", "dist_code", "court_complex_code", "court_number"]  # est_code optional
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = scraper_client.post("courtorder/by-court-number", {
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
            "est_code": body.get("est_code", ""),
            "court_number": body["court_number"],
            "order_type": body.get("order_type", "Both"),
        })
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


@api_view(["POST"])
@supabase_required
def courtorder_by_order_date(request):
    """POST /api/ecourts/courtorder/by-order-date/"""
    body = _parse_body(request)
    required = ["state_code", "dist_code", "court_complex_code",
                "from_date", "to_date"]  # est_code is optional for order-date tab
    missing = [f for f in required if not body.get(f)]
    if missing:
        return _error(f"Missing required fields: {missing}")
    try:
        result = scraper_client.post("courtorder/by-order-date", {
            "state_code": body["state_code"],
            "dist_code": body["dist_code"],
            "court_complex_code": body["court_complex_code"],
            "est_code": body.get("est_code", ""),
            "from_date": body["from_date"],
            "to_date": body["to_date"],
            "order_type": body.get("order_type", "Both"),
        })
        return JsonResponse(result)
    except Exception as e:
        return _scraper_error_response(e)


# ─────────────────────────────────────────────────────────────────────────────
# CRAWL TRIGGER — seed / populate eCourts master data collections
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["POST"])
@supabase_required
def seed_hierarchy(request):
    """
    POST /api/ecourts/v2/seed/

    Immediately seeds all 37 states into ecourts_states (synchronous, instant).
    Optionally enqueues deeper crawl as Celery background tasks.

    Body (all optional):
      crawl_districts  bool   enqueue districts-only crawl (default: false)
      crawl_full       bool   enqueue full hierarchy crawl (default: false)
      state_codes      list   limit to these codes e.g. ["8", "26"]
      dist_codes       list   limit to these districts (with single state)

    Returns:
      { seeded_states, task_id?, message }
    """
    from ecourt_scrapped.services.ecourts_crawler import (
        STATES, ensure_indexes, upsert_state,
    )
    from ecourt_scrapped.tasks import (
        crawl_ecourts_districts, crawl_ecourts_full,
    )

    body = _parse_body(request)
    do_districts = bool(body.get("crawl_districts", False))
    do_full      = bool(body.get("crawl_full", False))
    state_codes  = body.get("state_codes") or None
    dist_codes   = body.get("dist_codes") or None

    # Seed states synchronously (instant — just MongoDB writes)
    ensure_indexes()
    for s in STATES:
        upsert_state(s)
    logger.info(f"[seed_hierarchy] seeded {len(STATES)} states")

    response = {
        "seeded_states": len(STATES),
        "collections": "ecourts_states + ecourts_crawl_log",
        "message": f"Seeded {len(STATES)} states into ecourts_states.",
    }

    if do_full:
        task = crawl_ecourts_full.delay(
            state_codes=state_codes,
            dist_codes=dist_codes,
        )
        response["task_id"] = task.id
        response["message"] += (
            " Full hierarchy crawl enqueued — check Celery logs for progress."
        )
    elif do_districts:
        task = crawl_ecourts_districts.delay(state_codes=state_codes)
        response["task_id"] = task.id
        response["message"] += (
            " Districts crawl enqueued — check Celery logs for progress."
        )

    return JsonResponse(response)


@api_view(["GET"])
@supabase_required
def crawl_status(request):
    """GET /api/ecourts/v2/crawl/status/ — last crawl run info + stats."""
    from ecourt_scrapped.services.ecourts_crawler import read_stats, get_current_crawl
    cs = get_current_crawl()
    stats = read_stats()
    stats["currently_running"] = cs.running if cs else False
    return JsonResponse(stats)


# ─────────────────────────────────────────────────────────────────────────────
# DATA READ — serve pre-crawled master data from MongoDB
# ─────────────────────────────────────────────────────────────────────────────

@api_view(["GET"])
@supabase_required
def data_states(request):
    """GET /api/ecourts/v2/data/states/ — all states from ecourts_states."""
    from ecourt_scrapped.services.ecourts_crawler import read_states
    docs = read_states()
    return JsonResponse({"count": len(docs), "states": docs})


@api_view(["GET"])
@supabase_required
def data_districts(request):
    """GET /api/ecourts/v2/data/districts/?state_code=8"""
    from ecourt_scrapped.services.ecourts_crawler import read_districts
    state_code = request.GET.get("state_code", "")
    if not state_code:
        return _error("state_code query param is required")
    docs = read_districts(state_code)
    return JsonResponse({"state_code": state_code, "count": len(docs), "districts": docs})


@api_view(["GET"])
@supabase_required
def data_complexes(request):
    """GET /api/ecourts/v2/data/complexes/?state_code=8&dist_code=34"""
    from ecourt_scrapped.services.ecourts_crawler import read_complexes
    state_code = request.GET.get("state_code", "")
    dist_code = request.GET.get("dist_code", "")
    if not state_code or not dist_code:
        return _error("state_code and dist_code query params are required")
    docs = read_complexes(state_code, dist_code)
    return JsonResponse({"count": len(docs), "complexes": docs})


@api_view(["GET"])
@supabase_required
def data_establishments(request):
    """GET /api/ecourts/v2/data/establishments/?state_code=8&dist_code=34&complex_code=..."""
    from ecourt_scrapped.services.ecourts_crawler import read_establishments
    state_code = request.GET.get("state_code", "")
    dist_code = request.GET.get("dist_code", "")
    complex_code = request.GET.get("complex_code", "")
    if not all([state_code, dist_code, complex_code]):
        return _error("state_code, dist_code, complex_code query params are required")
    docs = read_establishments(state_code, dist_code, complex_code)
    return JsonResponse({"count": len(docs), "establishments": docs})


@api_view(["GET"])
@supabase_required
def data_courts(request):
    """GET /api/ecourts/v2/data/courts/?state_code=8&dist_code=34&complex_code=...&est_code=4"""
    from ecourt_scrapped.services.ecourts_crawler import read_courts
    state_code = request.GET.get("state_code", "")
    dist_code = request.GET.get("dist_code", "")
    complex_code = request.GET.get("complex_code", "")
    est_code = request.GET.get("est_code", "")
    if not all([state_code, dist_code, complex_code, est_code]):
        return _error("state_code, dist_code, complex_code, est_code are required")
    docs = read_courts(state_code, dist_code, complex_code, est_code)
    return JsonResponse({"count": len(docs), "courts": docs})


@api_view(["GET"])
@supabase_required
def data_police_stations(request):
    """GET /api/ecourts/v2/data/police-stations/?..."""
    from ecourt_scrapped.services.ecourts_crawler import read_police_stations
    state_code = request.GET.get("state_code", "")
    dist_code = request.GET.get("dist_code", "")
    complex_code = request.GET.get("complex_code", "")
    est_code = request.GET.get("est_code", "")
    if not all([state_code, dist_code, complex_code, est_code]):
        return _error("state_code, dist_code, complex_code, est_code are required")
    docs = read_police_stations(state_code, dist_code, complex_code, est_code)
    return JsonResponse({"count": len(docs), "police_stations": docs})


@api_view(["GET"])
@supabase_required
def data_case_types(request):
    """GET /api/ecourts/v2/data/case-types/?..."""
    from ecourt_scrapped.services.ecourts_crawler import read_case_types
    state_code = request.GET.get("state_code", "")
    dist_code = request.GET.get("dist_code", "")
    complex_code = request.GET.get("complex_code", "")
    est_code = request.GET.get("est_code", "")
    if not all([state_code, dist_code, complex_code, est_code]):
        return _error("state_code, dist_code, complex_code, est_code are required")
    docs = read_case_types(state_code, dist_code, complex_code, est_code)
    return JsonResponse({"count": len(docs), "case_types": docs})
