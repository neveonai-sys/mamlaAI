"""
Deprecated historical API views for the eCourts direct partner integration.

Drop-in replacement for ecourts_scraper views.  All responses are synchronous
(no job polling) because the external partner API returns data immediately.
"""
import re
import json
import traceback
import logging

from django.http import JsonResponse, HttpResponse
from rest_framework.decorators import api_view
from supabase_required import supabase_required

from ecourts_api import client, transformers
from ecourts_scraper.cache.cache_manager import EcourtsCacheManager

logger = logging.getLogger("django")

CNR_PATTERN = re.compile(r"^[A-Za-z0-9]{14,20}$")

# ── Case endpoints ──────────────────────────────────────────────────


@api_view(["GET"])
@supabase_required
def get_case_by_cnr(request, cnr):
    """GET /api/ecourts/case/<cnr>/  —  cached or live from partner API."""
    try:
        cnr = cnr.strip().upper()
        if not CNR_PATTERN.match(cnr):
            return JsonResponse({"error": "Invalid CNR format"}, status=400)

        cache = EcourtsCacheManager()
        cache_key = f"api:case:{cnr}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({
                "status": "success",
                "from_cache": True,
                "cached_at": cached["scraped_at"].isoformat() if cached.get("scraped_at") else None,
                "data": cached["data"],
            })

        raw = client.get_case(cnr)
        transformed = transformers.transform_case_detail(raw)
        cache.set(cache_key, "case_detail", transformed)

        return JsonResponse({
            "status": "success",
            "from_cache": False,
            "data": transformed,
        })
    except client.EcourtsApiError as e:
        return JsonResponse({"error": e.message, "code": e.code}, status=e.status_code)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["POST"])
@supabase_required
def refresh_case(request, cnr):
    """POST /api/ecourts/case/<cnr>/refresh/  —  queue re-scrape upstream."""
    try:
        cnr = cnr.strip().upper()
        if not CNR_PATTERN.match(cnr):
            return JsonResponse({"error": "Invalid CNR format"}, status=400)

        cache = EcourtsCacheManager()
        cache.invalidate(f"api:case:{cnr}")

        raw = client.refresh_case(cnr)
        data = raw.get("data", {})

        return JsonResponse({
            "status": "queued",
            "message": data.get("message", "Case refresh request queued"),
            "estimated_time": data.get("estimatedTime", "5-10 minutes"),
        }, status=202)
    except client.EcourtsApiError as e:
        return JsonResponse({"error": e.message, "code": e.code}, status=e.status_code)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_case_orders(request, cnr):
    """GET /api/ecourts/case/<cnr>/orders/  —  orders from cached case data."""
    try:
        cnr = cnr.strip().upper()
        if not CNR_PATTERN.match(cnr):
            return JsonResponse({"error": "Invalid CNR format"}, status=400)

        cache = EcourtsCacheManager()
        cached = cache.get(f"api:case:{cnr}")
        if not cached:
            return JsonResponse({
                "error": "Case not found in cache. Fetch the case first via GET /api/ecourts/case/<cnr>/",
            }, status=404)

        orders = cached.get("data", {}).get("orders", [])
        return JsonResponse({
            "status": "success",
            "cnr": cnr,
            "orders": orders,
            "total": len(orders),
        })
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def download_order(request, cnr, order_index):
    """GET /api/ecourts/case/<cnr>/orders/<idx>/download/

    Streams the PDF binary from the eCourts partner API back to the browser.
    Returns Content-Disposition: attachment so the browser triggers a file download.
    The partner API returns the PDF binary directly (not JSON), so we use
    client.get_order_stream() instead of client.get_order().
    """
    try:
        cnr = cnr.strip().upper()
        if not CNR_PATTERN.match(cnr):
            return JsonResponse({"error": "Invalid CNR format"}, status=400)

        cached_case = EcourtsCacheManager().get(f"api:case:{cnr}")
        if not cached_case:
            return JsonResponse({"error": "Case not cached. Fetch case first."}, status=404)

        orders = cached_case.get("data", {}).get("orders", [])
        if order_index < 0 or order_index >= len(orders):
            return JsonResponse({"error": "Order index out of range"}, status=400)

        filename = orders[order_index].get("filename", "")
        if not filename:
            return JsonResponse({"error": "No filename for this order"}, status=404)

        content, content_type = client.get_order_stream(cnr, filename)

        # Use only the last path segment as the download filename
        display_name = filename.split("/")[-1] if "/" in filename else filename
        if display_name and not display_name.lower().endswith(".pdf"):
            display_name += ".pdf"
        if not display_name:
            display_name = f"{cnr}-order-{order_index + 1}.pdf"

        response = HttpResponse(content, content_type=content_type or "application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{display_name}"'
        response["X-Content-Type-Options"] = "nosniff"
        return response
    except client.EcourtsApiError as e:
        return JsonResponse({"error": e.message, "code": e.code}, status=e.status_code)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


# ── Search ──────────────────────────────────────────────────────────


@api_view(["POST"])
@supabase_required
def search_cases(request):
    """
    POST /api/ecourts/search/

    Body: {
      "search_type": "advocate"|"party"|"litigant"|"judge"|"general",
      "query": "...",
      "page": 1,
      "page_size": 20,
      // optional filters
      "court_codes": [...],
      "case_statuses": [...],
      "case_types": [...],
      "filing_date_from": "YYYY-MM-DD",
      "filing_date_to": "YYYY-MM-DD",
    }
    """
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        search_type = data.get("search_type", "general")
        query = data.get("query", "").strip()
        page = max(int(data.get("page", 1)), 1)
        page_size = min(max(int(data.get("page_size", 20)), 1), 100)

        if not query:
            return JsonResponse({"error": "query is required"}, status=400)
        if len(query) < 2:
            return JsonResponse({"error": "query must be at least 2 characters"}, status=400)

        params = {"page": page, "pageSize": page_size}

        type_map = {
            "advocate": "advocates",
            "party": "litigants",
            "litigant": "litigants",
            "judge": "judges",
            "general": "query",
        }
        param_key = type_map.get(search_type, "query")
        params[param_key] = query

        for key, api_key in [
            ("court_codes", "courtCodes"),
            ("case_statuses", "caseStatuses"),
            ("case_types", "caseTypes"),
            ("filing_date_from", "filingDateFrom"),
            ("filing_date_to", "filingDateTo"),
        ]:
            val = data.get(key)
            if val:
                params[api_key] = val

        cache = EcourtsCacheManager()
        cache_key = client.make_search_cache_key(params)
        cached = cache.get(cache_key)
        if cached:
            enriched = transformers.enrich_cached_facets(cached["data"])
            return JsonResponse({
                "status": "success",
                "from_cache": True,
                "cached_at": cached["scraped_at"].isoformat() if cached.get("scraped_at") else None,
                "data": enriched,
            })

        raw = client.search(params)
        transformed = transformers.transform_search_results(raw)
        enriched = transformers.enrich_cached_facets(transformed)
        cache.set(cache_key, "case_search", enriched)

        return JsonResponse({
            "status": "success",
            "from_cache": False,
            "data": enriched,
        })
    except client.EcourtsApiError as e:
        return JsonResponse({"error": e.message, "code": e.code}, status=e.status_code)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


# ── Cause List ──────────────────────────────────────────────────────


@api_view(["GET"])
@supabase_required
def get_cause_list(request):
    """
    GET /api/ecourts/causelist/?state=DL&date=2024-02-15&advocate=name...

    Params: q, date, startDate, endDate, bench, judge, advocate, litigant,
            courtno, state, districtCode, courtComplexCode, listType,
            limit (max 100), offset
    """
    try:
        allowed_params = [
            "q", "date", "startDate", "endDate", "bench", "judge",
            "advocate", "litigant", "courtno", "state", "districtCode",
            "courtComplexCode", "listType", "limit", "offset",
        ]
        params = {}
        for key in allowed_params:
            val = request.GET.get(key, "").strip()
            if val:
                params[key] = val

        if not params:
            return JsonResponse({"error": "At least one search parameter is required"}, status=400)

        params.setdefault("limit", "100")

        cache = EcourtsCacheManager()
        cache_key = client.make_causelist_cache_key(params)
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({
                "status": "success",
                "from_cache": True,
                "cached_at": cached["scraped_at"].isoformat() if cached.get("scraped_at") else None,
                "data": cached["data"],
            })

        raw = client.get_causelist(params)
        transformed = transformers.transform_causelist_results(raw)
        cache.set(cache_key, "causelist", transformed)

        return JsonResponse({
            "status": "success",
            "from_cache": False,
            "data": transformed,
        })
    except client.EcourtsApiError as e:
        return JsonResponse({"error": e.message, "code": e.code}, status=e.status_code)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_cause_list_dates(request):
    """
    GET /api/ecourts/causelist/dates/?state=DL&districtCode=7...
    FREE with auth.
    """
    try:
        params = {}
        for key in ["state", "districtCode", "courtComplexCode", "courtNo"]:
            val = request.GET.get(key, "").strip()
            if val:
                params[key] = val

        if not params:
            return JsonResponse({"error": "At least one parameter required"}, status=400)

        raw = client.get_causelist_dates(params)
        dates = raw.get("data", raw) if isinstance(raw, dict) else raw

        return JsonResponse({
            "status": "success",
            "dates": dates,
        })
    except client.EcourtsApiError as e:
        return JsonResponse({"error": e.message, "code": e.code}, status=e.status_code)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


# ── Court structure (FREE — no credits consumed) ────────────────────


@api_view(["GET"])
@supabase_required
def get_court_structure(request):
    """GET /api/ecourts/court-structure/  —  aggregated top-level view."""
    try:
        cache = EcourtsCacheManager()
        cache_key = "api:court_structure:top"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({"status": "success", "data": cached["data"]})

        raw_states = client.get_states()
        states = transformers.transform_states(raw_states)

        from ecourts_scraper.constants import HIGH_COURT_CODES
        high_courts = []
        for code, info in sorted(HIGH_COURT_CODES.items(), key=lambda x: x[1]["name"]):
            high_courts.append({
                "id": code,
                "name": info["name"],
                "benches": info["benches"],
            })

        result = {
            "states": states,
            "total_states": len(states),
            "high_courts": high_courts,
        }
        cache.set(cache_key, "court_structure", result)
        return JsonResponse({"status": "success", "data": result})
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_states(request):
    """GET /api/ecourts/court-structure/states/"""
    try:
        cache = EcourtsCacheManager()
        cache_key = "api:court_structure:states"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({"status": "success", "data": cached["data"]})

        raw = client.get_states()
        data = transformers.transform_states(raw)
        cache.set(cache_key, "court_structure", data)
        return JsonResponse({"status": "success", "data": data})
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_districts(request, state_code):
    """GET /api/ecourts/court-structure/states/<state>/districts/"""
    try:
        cache = EcourtsCacheManager()
        cache_key = f"api:court_structure:districts:{state_code}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({"status": "success", "state": state_code, "data": cached["data"]})

        raw = client.get_districts(state_code)
        data = transformers.transform_districts(raw)
        cache.set(cache_key, "court_structure", data)
        return JsonResponse({"status": "success", "state": state_code, "data": data})
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_complexes(request, state_code, district_code):
    """GET /api/ecourts/court-structure/states/<state>/districts/<dist>/complexes/"""
    try:
        cache = EcourtsCacheManager()
        cache_key = f"api:court_structure:complexes:{state_code}:{district_code}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({
                "status": "success",
                "state": state_code,
                "district": district_code,
                "data": cached["data"],
            })

        raw = client.get_complexes(state_code, district_code)
        data = transformers.transform_complexes(raw)
        cache.set(cache_key, "court_structure", data)
        return JsonResponse({
            "status": "success",
            "state": state_code,
            "district": district_code,
            "data": data,
        })
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_courts(request, state_code, district_code, complex_code):
    """GET …/complexes/<complex>/courts/"""
    try:
        cache = EcourtsCacheManager()
        cache_key = f"api:court_structure:courts:{state_code}:{district_code}:{complex_code}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({
                "status": "success",
                "state": state_code,
                "district": district_code,
                "complex": complex_code,
                "data": cached["data"],
            })

        raw = client.get_courts(state_code, district_code, complex_code)
        data = transformers.transform_courts(raw)
        cache.set(cache_key, "court_structure", data)
        return JsonResponse({
            "status": "success",
            "state": state_code,
            "district": district_code,
            "complex": complex_code,
            "data": data,
        })
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_high_courts(request):
    """GET /api/ecourts/court-structure/high-courts/ — from constants."""
    try:
        from ecourts_scraper.constants import HIGH_COURT_CODES
        high_courts = []
        for code, info in sorted(HIGH_COURT_CODES.items(), key=lambda x: x[1]["name"]):
            high_courts.append({
                "id": code,
                "name": info["name"],
                "benches": info["benches"],
            })
        return JsonResponse({"status": "success", "data": high_courts})
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


# ── Default / pre-populated results ────────────────────────────────


VALID_DEFAULT_SECTIONS = {"cases", "lawyers", "litigants"}


@api_view(["GET"])
@supabase_required
def get_defaults(request, section):
    """
    GET /api/ecourts/defaults/<section>/

    Returns the latest pre-populated results for a section so that
    search pages show real data on first load without the user typing anything.

    Sections: cases | lawyers | litigants

    Results are populated by Celery Beat tasks:
      - cases / litigants : daily at 06:30 / 06:35
      - lawyers           : weekly on Monday at 06:40

    Response shape mirrors the search endpoint (same ``data`` object):
      { status, refreshed_at, data: { case_list, total, total_pages, ... } }

    If no defaults have been stored yet (e.g. first boot):
      { status: "empty" }
    """
    try:
        section = section.lower().strip()
        if section not in VALID_DEFAULT_SECTIONS:
            return JsonResponse(
                {"error": f"Unknown section '{section}'. Valid: {', '.join(VALID_DEFAULT_SECTIONS)}"},
                status=400,
            )

        cache = EcourtsCacheManager()
        cached = cache.get(f"defaults:{section}")
        if not cached:
            return JsonResponse({"status": "empty"})

        return JsonResponse({
            "status": "success",
            "refreshed_at": cached["scraped_at"].isoformat() if cached.get("scraped_at") else None,
            "data": cached["data"],
        })
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


# ── Job polling stub (for scraper compat) ───────────────────────────


@api_view(["GET"])
@supabase_required
def get_job_status(request, job_id):
    """
    Stub for scraper compatibility.  The direct API never creates jobs,
    so any job_id here is either from the old scraper or invalid.
    """
    return JsonResponse({
        "job_id": job_id,
        "status": "not_found",
        "message": "Direct API mode — no async jobs. Data is returned synchronously.",
    }, status=404)
