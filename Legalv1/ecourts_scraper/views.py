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
from ecourts_scraper.reference_data import EcourtsReferenceDataManager
from core.init_clients import get_mongo_client

logger = logging.getLogger("django")

CNR_PATTERN = re.compile(r"^[A-Za-z0-9]{14,20}$")


def _get_legaldb():
    return get_mongo_client()["legaldb"]


def _reference_response(doc: dict, *, extra: dict | None = None, status: int = 200):
    payload = {
        "status": "success",
        "reference_key": doc.get("reference_key"),
        "scope": doc.get("scope"),
        "source": doc.get("source"),
        "refreshed_at": doc.get("refreshed_at").isoformat() if doc.get("refreshed_at") else None,
        "meta": doc.get("meta", {}),
        "data": doc.get("data", []),
    }
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


@api_view(["GET"])
@supabase_required
def get_reference_section(request, section):
    """
    GET /api/ecourts/reference/<section>/
    Static reference payloads for the stitched eCourts terminal UI.
    """
    try:
        manager = EcourtsReferenceDataManager()
        doc = manager.get_static_section(section)
        if not doc:
            return JsonResponse({"error": f"Unknown reference section: {section}"}, status=404)
        return _reference_response(doc)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


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
        "registration_year": "2024", // required for HC party-name search
        "case_status": "pending" | "disposed" | "both", // optional for HC party-name search
        // HC: "high_court_id", "bench_code"
        // DC: "state_id", "district_id", "court_complex_id"
    }
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get("user_id", "")

        data = json.loads(request.body.decode("utf-8")) if request.body else {}
        search_type = (data.get("search_type", "advocate") or "advocate").strip().lower().replace("_", "-")
        query = data.get("query", "").strip()
        court_type = data.get("court_type", "high_court")
        page = max(int(data.get("page", 1)), 1)
        page_size = min(max(int(data.get("page_size", 20)), 1), 100)
        registration_year = str(data.get("registration_year", "")).strip()
        case_status = (data.get("case_status", "both") or "both").strip().lower()

        normalized_search_type = {
            "advocate": "advocate",
            "advocate-name": "advocate",
            "party": "party",
            "party-name": "party",
        }.get(search_type)

        if normalized_search_type is None:
            return JsonResponse({
                "error": (
                    "Unsupported scraper search_type. "
                    "The live scraper runtime currently supports advocate search on both courts and party-name search on High Court."
                ),
                "supported_search_types": ["advocate", "party"],
            }, status=400)

        if not query:
            return JsonResponse({"error": "query is required"}, status=400)
        if len(query) < 3:
            return JsonResponse({"error": "query must be at least 3 characters"}, status=400)
        if normalized_search_type == "party" and court_type != "high_court":
            return JsonResponse({
                "error": "Party-name scraper search is currently available for High Court only.",
                "supported_court_types": ["high_court"],
            }, status=400)
        if normalized_search_type == "party" and not registration_year:
            return JsonResponse({"error": "registration_year is required for party-name search"}, status=400)
        if normalized_search_type == "party" and (not registration_year.isdigit() or len(registration_year) != 4):
            return JsonResponse({"error": "registration_year must be a 4-digit year"}, status=400)
        if case_status not in {"pending", "disposed", "both"}:
            return JsonResponse({"error": "case_status must be one of pending, disposed, or both"}, status=400)

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
        cache_key = _build_search_cache_key(
            normalized_search_type,
            court_type,
            query,
            court_params,
            registration_year=registration_year,
            case_status=case_status,
        )
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

        if normalized_search_type == "party":
            job_id = jm.create_job(
                user_id,
                "search_party",
                {
                    "query": query,
                    "court_type": court_type,
                    "registration_year": registration_year,
                    "case_status": case_status,
                    "page": page,
                    "page_size": page_size,
                    **court_params,
                },
            )

            from ecourts_scraper.tasks import scrape_party_search
            scrape_party_search.delay(
                job_id=job_id,
                party_name=query,
                court_type=court_type,
                registration_year=registration_year,
                case_status=case_status,
                user_id=user_id,
                **court_params,
            )
        else:
            job_id = jm.create_job(
                user_id,
                "search_advocate",
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
    If the case is not cached, queues a scrape job (same as /case/<cnr>/) and returns 202.
    Orders are embedded in the case result by the scraper; no separate scrape needed.
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
            # Case not cached yet — reuse an already-running job or create a new one.
            # Deduplicates: CaseDetail fires getCaseByCnr + getCaseOrders simultaneously;
            # without this check both would spawn separate browser scrapes for the same CNR.
            supa_user = request.supabase_user
            user_id = supa_user.get("user_id", "")
            from ecourts_scraper.tasks import scrape_case_by_cnr
            jm = JobManager()
            existing = jm._col.find_one(
                {"user_id": user_id, "type": "case_by_cnr", "params.cnr": cnr,
                 "status": {"$in": ["queued", "processing"]}},
                sort=[("created_at", -1)],
            )
            if existing:
                job_id = existing["_id"]
            else:
                job_id = jm.create_job(user_id, "case_by_cnr", {"cnr": cnr})
                scrape_case_by_cnr.delay(job_id, cnr, user_id)
            return JsonResponse({
                "status": "pending",
                "job_id": job_id,
                "message": "Case not cached yet. Scrape queued — poll /api/ecourts/jobs/<job_id>/ then retry.",
                "estimated_seconds": 30,
            }, status=202)

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


def _build_search_cache_key(
    search_type: str,
    court_type: str,
    query: str,
    court_params: dict,
    *,
    registration_year: str = "",
    case_status: str = "both",
) -> str:
    """Build the same cache key the scraper uses for search results."""
    name = query.lower().replace(" ", "_")
    if court_type == "high_court":
        court = court_params.get("high_court_id", "")
        bench = court_params.get("bench_code", "")
        if search_type == "party":
            return f"hc:search:party:{court}:{bench}:{registration_year}:{case_status}:{name}"
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
        &causelist_type=daily

    Returns cached cause list if available; otherwise 202 + job_id.
    """
    try:
        supa_user = request.supabase_user
        user_id = supa_user.get("user_id", "")

        date = request.GET.get("date", "").strip()
        hc_id = request.GET.get("high_court_id", "").strip()
        bench_code = request.GET.get("bench_code", "").strip()
        causelist_type = request.GET.get("causelist_type", "daily").strip()

        if not date:
            return JsonResponse({"error": "date query parameter is required (YYYY-MM-DD)"}, status=400)
        if not hc_id or not bench_code:
            return JsonResponse({"error": "high_court_id and bench_code are required"}, status=400)
        if causelist_type != "daily":
            return JsonResponse({
                "error": "The live High Court cause-list scraper currently supports daily lists only.",
                "supported_causelist_types": ["daily"],
            }, status=400)

        params = {
            "date": date,
            "high_court_id": hc_id,
            "bench_code": bench_code,
            "causelist_type": causelist_type,
            "query": "",
            "court_no": "",
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

        manager = EcourtsReferenceDataManager()
        district_states = manager.get_district_states()

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
                    "states": district_states.get("data", []),
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
        manager = EcourtsReferenceDataManager()
        return _reference_response(manager.get_district_states())

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
        manager = EcourtsReferenceDataManager()
        doc = manager.get_districts(state_name)

        if not doc.get("data"):
            return JsonResponse({"error": f"No districts found for state: {state_name}"}, status=404)

        return _reference_response(doc, extra={"state": state_name})

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_complexes_by_district(request, state_name, district_name):
    """
    GET /api/ecourts/court-structure/district/states/<state>/districts/<district>/complexes/
    Returns stored district court complexes when available, otherwise a synthetic
    district-level fallback complex so the new frontend can keep its cascade intact.
    """
    try:
        manager = EcourtsReferenceDataManager()
        doc = manager.get_complexes(state_name, district_name)
        if not doc.get("data"):
            return JsonResponse(
                {"error": f"No court complexes found for {district_name}, {state_name}"},
                status=404,
            )
        return _reference_response(doc, extra={"state": state_name, "district": district_name})
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
        manager = EcourtsReferenceDataManager()
        complexes_doc = manager.get_complexes(state_name, district_name)
        complexes = complexes_doc.get("data", [])
        if not complexes:
            return JsonResponse(
                {"error": f"No courts found for {district_name}, {state_name}"},
                status=404,
            )

        primary_complex_id = str(complexes[0].get("id", ""))
        doc = manager.get_courts(state_name, district_name, primary_complex_id)
        if not doc.get("data"):
            return JsonResponse(
                {"error": f"No courts found for {district_name}, {state_name}"},
                status=404,
            )

        return _reference_response(
            doc,
            extra={
                "state": state_name,
                "district": district_name,
                "complex_id": primary_complex_id,
            },
        )

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@supabase_required
def get_courts_by_complex(request, state_name, district_name, complex_code):
    """
    GET /api/ecourts/court-structure/district/states/<state>/districts/<district>/complexes/<complex>/courts/
    Returns courts scoped to a selected district court complex.
    """
    try:
        manager = EcourtsReferenceDataManager()
        doc = manager.get_courts(state_name, district_name, complex_code)
        if not doc.get("data"):
            return JsonResponse(
                {"error": f"No courts found for complex {complex_code} in {district_name}, {state_name}"},
                status=404,
            )

        return _reference_response(
            doc,
            extra={
                "state": state_name,
                "district": district_name,
                "complex_id": complex_code,
            },
        )

    except Exception as e:
        logger.error(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=500)
