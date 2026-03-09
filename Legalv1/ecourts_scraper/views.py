"""
API views for eCourts scraper.
All endpoints follow the existing Mamla.AI patterns:
  @api_view + @supabase_required + JsonResponse
"""
import re
import json
import traceback
import logging
from django.http import JsonResponse
from rest_framework.decorators import api_view
from supabase_required import supabase_required

from ecourts_scraper.agent.job_manager import JobManager
from ecourts_scraper.cache.cache_manager import EcourtsCacheManager
from core.init_clients import get_mongo_client

logger = logging.getLogger("django")

CNR_PATTERN = re.compile(r"^[A-Za-z0-9]{14,20}$")


def _get_legaldb():
    return get_mongo_client()["legaldb"]


@api_view(["GET"])
@supabase_required
def get_case_by_cnr(request, cnr):
    """
    GET /api/ecourts/case/<cnr>/
    Returns cached case data if available, otherwise queues a scrape job.
    """
    try:
        cnr = cnr.strip().upper()
        if not CNR_PATTERN.match(cnr):
            return JsonResponse({"error": "Invalid CNR format"}, status=400)

        supa_user = request.supabase_user
        user_id = supa_user.get("user_id", "")

        cache = EcourtsCacheManager()

        for prefix in ("hc:case:", "dc:case:"):
            cached = cache.get(f"{prefix}{cnr}")
            if cached:
                return JsonResponse({
                    "status": "success",
                    "from_cache": True,
                    "cached_at": cached["scraped_at"].isoformat() if cached.get("scraped_at") else None,
                    "data": cached["data"],
                }, status=200)

        from ecourts_scraper.tasks import scrape_case_by_cnr
        jm = JobManager()
        job_id = jm.create_job(user_id, "case_by_cnr", {"cnr": cnr})
        scrape_case_by_cnr.delay(job_id, cnr, user_id)

        return JsonResponse({
            "status": "pending",
            "job_id": job_id,
            "message": f"Case data not cached. Scrape job queued. Poll /api/ecourts/jobs/{job_id}/ for status.",
            "estimated_seconds": 30,
        }, status=202)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["POST"])
@supabase_required
def refresh_case(request, cnr):
    """
    POST /api/ecourts/case/<cnr>/refresh/
    Force a fresh scrape of the case, bypassing cache.
    """
    try:
        cnr = cnr.strip().upper()
        if not CNR_PATTERN.match(cnr):
            return JsonResponse({"error": "Invalid CNR format"}, status=400)

        supa_user = request.supabase_user
        user_id = supa_user.get("user_id", "")

        cache = EcourtsCacheManager()
        cache.invalidate(f"hc:case:{cnr}")
        cache.invalidate(f"dc:case:{cnr}")

        from ecourts_scraper.tasks import scrape_case_by_cnr
        jm = JobManager()
        job_id = jm.create_job(user_id, "case_refresh", {"cnr": cnr})
        scrape_case_by_cnr.delay(job_id, cnr, user_id)

        return JsonResponse({
            "status": "queued",
            "job_id": job_id,
            "message": "Refresh queued. Poll /api/ecourts/jobs/{job_id}/ for status.",
            "estimated_seconds": 30,
        }, status=202)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_job_status(request, job_id):
    """
    GET /api/ecourts/jobs/<job_id>/
    Poll the status of an async scrape job.
    """
    try:
        jm = JobManager()
        job = jm.get_job(job_id)
        if not job:
            return JsonResponse({"error": "Job not found"}, status=404)

        response = {
            "job_id": job["job_id"],
            "type": job.get("type"),
            "status": job.get("status"),
            "progress": job.get("progress"),
            "created_at": job["created_at"].isoformat() if job.get("created_at") else None,
            "completed_at": job["completed_at"].isoformat() if job.get("completed_at") else None,
            "error": job.get("error"),
        }

        if job.get("status") == "completed" and job.get("result"):
            response["result"] = job["result"]

        return JsonResponse(response, status=200)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["POST"])
@supabase_required
def search_cases(request):
    """
    POST /api/ecourts/search/
    Search cases by advocate name or party name.
    Body: {
        "search_type": "advocate" | "party",
        "query": "name",
        "court_type": "high_court" | "district_court",
        "page": 1,          // optional, default 1
        "page_size": 20,     // optional, default 20, max 100
        // HC: "high_court_id", "bench_code"
        // DC: "state_id", "district_id", "court_complex_id"
    }
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get("user_id", "")

        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        search_type = data.get("search_type", "advocate")
        query = data.get("query", "").strip()
        court_type = data.get("court_type", "high_court")
        page = max(int(data.get("page", 1)), 1)
        page_size = min(max(int(data.get("page_size", 20)), 1), 100)

        if not query:
            return JsonResponse({"error": "query is required"}, status=400)
        if len(query) < 3:
            return JsonResponse({"error": "query must be at least 3 characters"}, status=400)

        court_params = {}

        if court_type == "high_court":
            hc_id = data.get("high_court_id")
            bench = data.get("bench_code")
            if not hc_id or not bench:
                return JsonResponse(
                    {"error": "high_court_id and bench_code are required for HC search"},
                    status=400,
                )
            court_params = {"high_court_id": hc_id, "bench_code": bench}
        else:
            state_id = data.get("state_id")
            district_id = data.get("district_id")
            court_complex_id = data.get("court_complex_id")
            if not all([state_id, district_id, court_complex_id]):
                return JsonResponse(
                    {"error": "state_id, district_id, and court_complex_id are required for DC search"},
                    status=400,
                )
            court_params = {
                "state_id": state_id,
                "district_id": district_id,
                "court_complex_id": court_complex_id,
            }

        cache = EcourtsCacheManager()
        cache_key = _build_search_cache_key(court_type, query, court_params)
        cached = cache.get(cache_key)
        if cached:
            case_list = cached.get("data", {}).get("case_list", [])
            total = len(case_list)
            start = (page - 1) * page_size
            end = start + page_size
            return JsonResponse({
                "status": "success",
                "from_cache": True,
                "cached_at": cached["scraped_at"].isoformat() if cached.get("scraped_at") else None,
                "data": {
                    "case_list": case_list[start:end],
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size if total else 0,
                },
            }, status=200)

        jm = JobManager()
        job_id = jm.create_job(
            user_id,
            f"search_{search_type}",
            {"query": query, "court_type": court_type, "page": page, "page_size": page_size, **court_params},
        )

        from ecourts_scraper.tasks import scrape_advocate_search
        scrape_advocate_search.delay(
            job_id=job_id,
            advocate_name=query,
            court_type=court_type,
            user_id=user_id,
            **court_params,
        )

        return JsonResponse({
            "status": "queued",
            "job_id": job_id,
            "message": f"Search queued. Poll /api/ecourts/jobs/{job_id}/ for status.",
            "estimated_seconds": 45,
        }, status=202)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# Order listing + PDF download
# =====================================================================

@api_view(["GET"])
@supabase_required
def get_case_orders(request, cnr):
    """
    GET /api/ecourts/case/<cnr>/orders/
    Returns the orders list from cached case data.
    """
    try:
        cnr = cnr.strip().upper()
        if not CNR_PATTERN.match(cnr):
            return JsonResponse({"error": "Invalid CNR format"}, status=400)

        cache = EcourtsCacheManager()
        case_data = None
        court_prefix = None
        for prefix in ("hc:case:", "dc:case:"):
            cached = cache.get(f"{prefix}{cnr}")
            if cached:
                case_data = cached.get("data", {})
                court_prefix = prefix.split(":")[0]
                break

        if not case_data:
            return JsonResponse({
                "error": "Case not found in cache. Fetch the case first via GET /api/ecourts/case/<cnr>/",
            }, status=404)

        orders = case_data.get("orders", [])
        return JsonResponse({
            "status": "success",
            "cnr": cnr,
            "court_type": court_prefix,
            "orders": orders,
            "total": len(orders),
        }, status=200)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def download_order_pdf(request, cnr, order_index):
    """
    GET /api/ecourts/case/<cnr>/orders/<order_index>/download/
    Downloads an order PDF. order_index is 0-based index in the orders list.

    If already cached, returns immediately. Otherwise queues a download job.
    """
    try:
        cnr = cnr.strip().upper()
        if not CNR_PATTERN.match(cnr):
            return JsonResponse({"error": "Invalid CNR format"}, status=400)

        try:
            order_idx = int(order_index)
        except ValueError:
            return JsonResponse({"error": "order_index must be an integer"}, status=400)

        supa_user = request.supabase_user
        user_id = supa_user.get("user_id", "")

        cache = EcourtsCacheManager()

        for prefix in ("hc", "dc"):
            pdf_key = f"{prefix}:order_pdf:{cnr}:{order_idx}"
            cached_pdf = cache.get(pdf_key)
            if cached_pdf:
                return JsonResponse({
                    "status": "success",
                    "from_cache": True,
                    "data": cached_pdf["data"],
                }, status=200)

        from ecourts_scraper.tasks import download_order_pdf_task
        jm = JobManager()
        job_id = jm.create_job(user_id, "order_pdf_download", {
            "cnr": cnr, "order_index": order_idx,
        })
        download_order_pdf_task.delay(job_id, cnr, order_idx, user_id)

        return JsonResponse({
            "status": "queued",
            "job_id": job_id,
            "message": f"PDF download queued. Poll /api/ecourts/jobs/{job_id}/ for status.",
            "estimated_seconds": 45,
        }, status=202)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


def _build_search_cache_key(court_type: str, query: str, court_params: dict) -> str:
    """Build the same cache key the scraper uses for search results."""
    name = query.lower().replace(" ", "_")
    if court_type == "high_court":
        court = court_params.get("high_court_id", "")
        bench = court_params.get("bench_code", "")
        return f"hc:search:{court}:{bench}:{name}"
    else:
        state = court_params.get("state_id", "")
        district = court_params.get("district_id", "")
        court = court_params.get("court_complex_id", "")
        return f"dc:search:{state}:{district}:{court}:{name}"


# =====================================================================
# Cause List endpoints
# =====================================================================

@api_view(["GET"])
@supabase_required
def get_cause_list(request):
    """
    GET /api/ecourts/causelist/?date=YYYY-MM-DD&high_court_id=5&bench_code=1
        &causelist_type=daily|advocate|courtroom&query=...&court_no=...

    Returns cached cause list if available; otherwise 202 + job_id.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get("user_id", "")

        date = request.GET.get("date", "").strip()
        hc_id = request.GET.get("high_court_id", "").strip()
        bench_code = request.GET.get("bench_code", "").strip()
        causelist_type = request.GET.get("causelist_type", "daily").strip()
        query = request.GET.get("query", "").strip()
        court_no = request.GET.get("court_no", "").strip()

        if not date:
            return JsonResponse({"error": "date query parameter is required (YYYY-MM-DD)"}, status=400)
        if not hc_id or not bench_code:
            return JsonResponse({"error": "high_court_id and bench_code are required"}, status=400)

        params = {
            "date": date,
            "high_court_id": hc_id,
            "bench_code": bench_code,
            "causelist_type": causelist_type,
            "query": query,
            "court_no": court_no,
        }

        cache = EcourtsCacheManager()
        cache_key = f"hc:causelist:{hc_id}:{bench_code}:{date}:{causelist_type}:{query.lower().replace(' ', '_')}"
        cached = cache.get(cache_key)
        if cached:
            return JsonResponse({
                "status": "success",
                "from_cache": True,
                "cached_at": cached["scraped_at"].isoformat() if cached.get("scraped_at") else None,
                "data": cached["data"],
            }, status=200)

        from ecourts_scraper.tasks import scrape_cause_list
        jm = JobManager()
        job_id = jm.create_job(user_id, "causelist", params)
        scrape_cause_list.delay(job_id, user_id=user_id, **params)

        return JsonResponse({
            "status": "queued",
            "job_id": job_id,
            "message": f"Cause list scrape queued. Poll /api/ecourts/jobs/{job_id}/ for status.",
            "estimated_seconds": 30,
        }, status=202)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_available_cause_list_dates(request):
    """
    GET /api/ecourts/causelist/dates/?high_court_id=5&bench_code=1

    Returns dates for which we have cached cause lists for this court.
    """
    try:
        hc_id = request.GET.get("high_court_id", "").strip()
        bench_code = request.GET.get("bench_code", "").strip()

        if not hc_id or not bench_code:
            return JsonResponse({"error": "high_court_id and bench_code are required"}, status=400)

        cache = EcourtsCacheManager()
        prefix = f"hc:causelist:{hc_id}:{bench_code}:"
        dates = cache.get_keys_by_prefix(prefix)

        extracted_dates = set()
        for key in dates:
            parts = key.replace(prefix, "").split(":")
            if parts:
                extracted_dates.add(parts[0])

        return JsonResponse({
            "status": "success",
            "dates": sorted(extracted_dates, reverse=True),
        }, status=200)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


# =====================================================================
# Court Structure endpoints (reads existing state_district_court_data)
# =====================================================================

@api_view(["GET"])
@supabase_required
def get_court_structure(request):
    """
    GET /api/ecourts/court-structure/
    Returns the top-level court structure: high courts + district court states.
    """
    try:
        from ecourts_scraper.constants import HIGH_COURT_CODES

        db = _get_legaldb()
        states = db["state_district_court_data"].distinct("state_name")
        states.sort()

        high_courts = []
        for code, info in sorted(HIGH_COURT_CODES.items(), key=lambda x: x[1]["name"]):
            high_courts.append({
                "id": code,
                "name": info["name"],
                "benches": info["benches"],
            })

        return JsonResponse({
            "status": "success",
            "data": {
                "high_courts": high_courts,
                "district_courts": {
                    "states": [{"name": s} for s in states],
                },
            },
        }, status=200)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_high_courts(request):
    """
    GET /api/ecourts/court-structure/high-courts/
    Returns all high courts with their benches from constants.
    """
    try:
        from ecourts_scraper.constants import HIGH_COURT_CODES

        high_courts = []
        for code, info in sorted(HIGH_COURT_CODES.items(), key=lambda x: x[1]["name"]):
            high_courts.append({
                "id": code,
                "name": info["name"],
                "benches": info["benches"],
            })

        return JsonResponse({
            "status": "success",
            "data": high_courts,
        }, status=200)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_district_states(request):
    """
    GET /api/ecourts/court-structure/district/states/
    Returns all states for district courts.
    """
    try:
        db = _get_legaldb()
        states = db["state_district_court_data"].distinct("state_name")
        states.sort()

        return JsonResponse({
            "status": "success",
            "data": [{"name": s} for s in states],
        }, status=200)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_district_by_state(request, state_name):
    """
    GET /api/ecourts/court-structure/district/states/<state_name>/districts/
    Returns districts within a state.
    """
    try:
        db = _get_legaldb()
        districts = db["state_district_court_data"].distinct(
            "district_name", {"state_name": state_name}
        )
        districts.sort()

        if not districts:
            return JsonResponse({"error": f"No districts found for state: {state_name}"}, status=404)

        return JsonResponse({
            "status": "success",
            "state": state_name,
            "data": [{"name": d} for d in districts],
        }, status=200)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_courts_by_district(request, state_name, district_name):
    """
    GET /api/ecourts/court-structure/district/states/<state_name>/districts/<district_name>/courts/
    Returns courts within a district.
    """
    try:
        db = _get_legaldb()
        cursor = db["state_district_court_data"].find(
            {"state_name": state_name, "district_name": district_name},
            {"_id": 0, "court_name": 1, "court_platform_assigned_id": 1},
        )
        courts = []
        for doc in cursor:
            courts.append({
                "name": doc.get("court_name", ""),
                "platform_id": doc.get("court_platform_assigned_id", ""),
            })
        courts.sort(key=lambda c: c["name"])

        if not courts:
            return JsonResponse(
                {"error": f"No courts found for {district_name}, {state_name}"},
                status=404,
            )

        return JsonResponse({
            "status": "success",
            "state": state_name,
            "district": district_name,
            "data": courts,
        }, status=200)

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)
