"""
Celery tasks for eCourts scraping.
These are the entry points that the ScrapeAgent state machine runs inside.
"""
import logging
import traceback
from celery import shared_task

from ecourts_scraper.agent.job_manager import JobManager
from ecourts_scraper.constants import HC_RATE_LIMIT_PER_MIN, DC_RATE_LIMIT_PER_MIN
from ecourts_scraper.reference_data import EcourtsReferenceDataManager

logger = logging.getLogger("django")


def _get_rate_limiters():
    from ecourts_scraper.infra.rate_limiter import RateLimiter
    return (
        RateLimiter("hcservices.ecourts.gov.in", HC_RATE_LIMIT_PER_MIN),
        RateLimiter("services.ecourts.gov.in", DC_RATE_LIMIT_PER_MIN),
    )


def _detect_court_type(cnr: str) -> str:
    """
    Detect whether a CNR belongs to a High Court or District Court.
    HC CNRs typically contain 'HC' in positions 2-4 (e.g. DLHC01...).
    """
    cnr_upper = cnr.upper()
    if len(cnr_upper) >= 4 and "HC" in cnr_upper[:6]:
        return "high_court"
    return "district_court"


@shared_task(
    name="ecourts_scraper.tasks.scrape_case_by_cnr",
    queue="ecourts_realtime",
    rate_limit="10/m",
    max_retries=0,
)
def scrape_case_by_cnr(job_id: str, cnr: str, user_id: str = ""):
    """Scrape a case by CNR number. Auto-detects HC vs DC."""
    from ecourts_scraper.agent.state_machine import ScrapeAgent, AgentContext
    from ecourts_scraper.scrapers.highcourt import HighCourtScraper
    from ecourts_scraper.scrapers.districtcourt import DistrictCourtScraper

    jm = JobManager()
    hc_rate_limiter, dc_rate_limiter = _get_rate_limiters()
    court_type = _detect_court_type(cnr)

    if court_type == "high_court":
        scraper = HighCourtScraper()
        rate_limiter = hc_rate_limiter
    else:
        scraper = DistrictCourtScraper()
        rate_limiter = dc_rate_limiter

    agent = ScrapeAgent(scraper, jm)
    ctx = AgentContext(
        job_id=job_id,
        scraper_name=court_type,
        scraper_method="case_by_cnr",
        params={"cnr": cnr, "_method": "case_by_cnr"},
        rate_limiter=rate_limiter,
    )

    try:
        result = agent.execute(ctx)
        if result:
            jm.complete_job(job_id, result)
            return {"status": "completed", "job_id": job_id, "cached": ctx.cached}
        else:
            jm.fail_job(job_id, ctx.error or "No result returned")
            return {"status": "failed", "job_id": job_id, "error": ctx.error}
    except Exception as e:
        logger.error("scrape_case_by_cnr failed: %s\n%s", e, traceback.format_exc())
        jm.fail_job(job_id, str(e))
        return {"status": "failed", "job_id": job_id, "error": str(e)}
    finally:
        agent.cleanup(ctx)


@shared_task(
    name="ecourts_scraper.tasks.scrape_advocate_search",
    queue="ecourts_realtime",
    rate_limit="5/m",
    max_retries=0,
)
def scrape_advocate_search(
    job_id: str,
    advocate_name: str,
    court_type: str,
    user_id: str = "",
    **court_params,
):
    """Search cases by advocate name on HC or DC site."""
    from ecourts_scraper.agent.state_machine import ScrapeAgent, AgentContext
    from ecourts_scraper.scrapers.highcourt import HighCourtScraper
    from ecourts_scraper.scrapers.districtcourt import DistrictCourtScraper

    jm = JobManager()
    hc_rate_limiter, dc_rate_limiter = _get_rate_limiters()

    params = {"advocate_name": advocate_name, "_method": "search_advocate"}
    params.update(court_params)

    if court_type == "high_court":
        scraper = HighCourtScraper()
        rate_limiter = hc_rate_limiter
    else:
        scraper = DistrictCourtScraper()
        rate_limiter = dc_rate_limiter

    agent = ScrapeAgent(scraper, jm)
    ctx = AgentContext(
        job_id=job_id,
        scraper_name=court_type,
        scraper_method="search_advocate",
        params=params,
        rate_limiter=rate_limiter,
    )

    try:
        result = agent.execute(ctx)
        if result:
            jm.complete_job(job_id, result)
            return {"status": "completed", "job_id": job_id}
        else:
            jm.fail_job(job_id, ctx.error or "No result returned")
            return {"status": "failed", "job_id": job_id, "error": ctx.error}
    except Exception as e:
        logger.error("scrape_advocate_search failed: %s\n%s", e, traceback.format_exc())
        jm.fail_job(job_id, str(e))
        return {"status": "failed", "job_id": job_id, "error": str(e)}
    finally:
        agent.cleanup(ctx)


@shared_task(
    name="ecourts_scraper.tasks.scrape_party_search",
    queue="ecourts_realtime",
    rate_limit="5/m",
    max_retries=0,
)
def scrape_party_search(
    job_id: str,
    party_name: str,
    court_type: str,
    registration_year: str,
    case_status: str = "both",
    user_id: str = "",
    **court_params,
):
    """Search High Court cases by petitioner/respondent name."""
    from ecourts_scraper.agent.state_machine import ScrapeAgent, AgentContext
    from ecourts_scraper.scrapers.highcourt import HighCourtScraper

    jm = JobManager()
    hc_rate_limiter, _ = _get_rate_limiters()

    if court_type != "high_court":
        error = "Party-name scraper search is currently available for High Court only."
        jm.fail_job(job_id, error)
        return {"status": "failed", "job_id": job_id, "error": error}

    params = {
        "party_name": party_name,
        "registration_year": str(registration_year),
        "case_status": case_status,
        "_method": "search_party",
    }
    params.update(court_params)

    scraper = HighCourtScraper()
    agent = ScrapeAgent(scraper, jm)
    ctx = AgentContext(
        job_id=job_id,
        scraper_name="high_court",
        scraper_method="search_party",
        params=params,
        rate_limiter=hc_rate_limiter,
    )

    try:
        result = agent.execute(ctx)
        if result:
            jm.complete_job(job_id, result)
            return {"status": "completed", "job_id": job_id}
        else:
            jm.fail_job(job_id, ctx.error or "No result returned")
            return {"status": "failed", "job_id": job_id, "error": ctx.error}
    except Exception as e:
        logger.error("scrape_party_search failed: %s\n%s", e, traceback.format_exc())
        jm.fail_job(job_id, str(e))
        return {"status": "failed", "job_id": job_id, "error": str(e)}
    finally:
        agent.cleanup(ctx)


@shared_task(
    name="ecourts_scraper.tasks.download_order_pdf_task",
    queue="ecourts_realtime",
    rate_limit="5/m",
    max_retries=0,
)
def download_order_pdf_task(job_id: str, cnr: str, order_index: int, user_id: str = ""):
    """
    Download an order PDF by first fetching the case page, then clicking
    the order link at the given index.
    """
    import base64

    jm = JobManager()
    hc_rate_limiter, dc_rate_limiter = _get_rate_limiters()
    court_type = _detect_court_type(cnr)

    try:
        from ecourts_scraper.cache.cache_manager import EcourtsCacheManager
        cache = EcourtsCacheManager()

        prefix = "hc" if court_type == "high_court" else "dc"
        cached_case = cache.get(f"{prefix}:case:{cnr}")
        if not cached_case:
            jm.fail_job(job_id, "Case not in cache. Scrape the case first.")
            return {"status": "failed", "job_id": job_id, "error": "Case not in cache"}

        orders = cached_case.get("data", {}).get("orders", [])
        if order_index < 0 or order_index >= len(orders):
            jm.fail_job(job_id, f"Order index {order_index} out of range (0-{len(orders)-1})")
            return {"status": "failed", "job_id": job_id, "error": "Order index out of range"}

        jm.update_progress(job_id, "processing", "downloading_pdf")

        from ecourts_scraper.infra.browser_pool import browser_pool
        from ecourts_scraper.agent.state_machine import ScrapeAgent, AgentContext
        from ecourts_scraper.scrapers.highcourt import HighCourtScraper
        from ecourts_scraper.scrapers.districtcourt import DistrictCourtScraper

        rate_limiter = hc_rate_limiter if court_type == "high_court" else dc_rate_limiter
        if not rate_limiter.acquire(timeout=60):
            jm.fail_job(job_id, "Rate limit timeout")
            return {"status": "failed", "job_id": job_id, "error": "Rate limit timeout"}

        scraper = HighCourtScraper() if court_type == "high_court" else DistrictCourtScraper()

        context = browser_pool.acquire_context()
        page = browser_pool.new_page(context)

        try:
            scraper.navigate(page, {"cnr": cnr, "_method": "case_by_cnr"})
            solved = scraper.solve_captcha(page, 0)
            if not solved:
                jm.fail_job(job_id, "CAPTCHA solve failed during PDF download")
                return {"status": "failed", "job_id": job_id, "error": "CAPTCHA failed"}

            scraper.fill_form(page, {"cnr": cnr, "_method": "case_by_cnr"})
            submit_result = scraper.submit_and_check(page)
            if submit_result != "success":
                jm.fail_job(job_id, f"Form submission returned: {submit_result}")
                return {"status": "failed", "job_id": job_id, "error": submit_result}

            import time
            time.sleep(2)

            order_links = page.locator("table.order_table a, table.order_table button").all()
            if order_index >= len(order_links):
                jm.fail_job(job_id, f"Order link {order_index} not found on page ({len(order_links)} links)")
                return {"status": "failed", "job_id": job_id, "error": "Order link not found"}

            with page.expect_download(timeout=30000) as download_info:
                order_links[order_index].click()

            download = download_info.value
            pdf_path = download.path()
            if pdf_path:
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
                filename = download.suggested_filename or f"order_{cnr}_{order_index}.pdf"
            else:
                jm.fail_job(job_id, "PDF download returned no file")
                return {"status": "failed", "job_id": job_id, "error": "No file from download"}

            result = {
                "cnr": cnr,
                "order_index": order_index,
                "filename": filename,
                "content_type": "application/pdf",
                "pdf_base64": pdf_b64,
                "size_bytes": len(pdf_bytes),
            }

            pdf_cache_key = f"{prefix}:order_pdf:{cnr}:{order_index}"
            cache.set(pdf_cache_key, "order_pdf", result, scraper.get_source_site())

            jm.complete_job(job_id, result)
            return {"status": "completed", "job_id": job_id}

        finally:
            browser_pool.release_context(context)

    except Exception as e:
        logger.error("download_order_pdf_task failed: %s\n%s", e, traceback.format_exc())
        jm.fail_job(job_id, str(e))
        return {"status": "failed", "job_id": job_id, "error": str(e)}


@shared_task(
    name="ecourts_scraper.tasks.scrape_cause_list",
    queue="ecourts_realtime",
    rate_limit="5/m",
    max_retries=0,
)
def scrape_cause_list(
    job_id: str,
    date: str = "",
    high_court_id: str = "",
    bench_code: str = "",
    causelist_type: str = "daily",
    query: str = "",
    court_no: str = "",
    user_id: str = "",
    **extra_params,
):
    """Scrape cause list for a given HC + date."""
    from ecourts_scraper.agent.state_machine import ScrapeAgent, AgentContext
    from ecourts_scraper.scrapers.causelist import CauseListScraper

    jm = JobManager()
    hc_rate_limiter, _ = _get_rate_limiters()

    params = {
        "_method": "causelist",
        "date": date,
        "high_court_id": high_court_id,
        "bench_code": bench_code,
        "causelist_type": causelist_type,
        "query": query,
        "court_no": court_no,
    }

    scraper = CauseListScraper()
    agent = ScrapeAgent(scraper, jm)
    ctx = AgentContext(
        job_id=job_id,
        scraper_name="high_court_causelist",
        scraper_method="causelist",
        params=params,
        rate_limiter=hc_rate_limiter,
    )

    try:
        result = agent.execute(ctx)
        if result:
            jm.complete_job(job_id, result)
            return {"status": "completed", "job_id": job_id, "cached": ctx.cached}
        else:
            jm.fail_job(job_id, ctx.error or "No result returned")
            return {"status": "failed", "job_id": job_id, "error": ctx.error}
    except Exception as e:
        logger.error("scrape_cause_list failed: %s\n%s", e, traceback.format_exc())
        jm.fail_job(job_id, str(e))
        return {"status": "failed", "job_id": job_id, "error": str(e)}
    finally:
        agent.cleanup(ctx)


@shared_task(
    name="ecourts_scraper.tasks.cleanup_expired_cache",
    queue="ecourts_background",
)
def cleanup_expired_cache():
    """Remove expired cache entries (also handled by MongoDB TTL index)."""
    from ecourts_scraper.cache.cache_manager import EcourtsCacheManager
    cache = EcourtsCacheManager()
    count = cache.cleanup_expired()
    logger.info("Cleaned up %d expired cache entries", count)
    return {"cleaned": count}


@shared_task(
    name="ecourts_scraper.tasks.refresh_subscribed_causelists",
    queue="ecourts_background",
    rate_limit="2/m",
)
def refresh_subscribed_causelists():
    """
    Find all unique subscribed courts across users, then queue cause list
    scrapes for today's date.
    """
    from datetime import date as date_type
    from core.init_clients import get_mongo_client

    db = get_mongo_client()["legaldb"]
    today = date_type.today().isoformat()
    jm = JobManager()

    try:
        pipeline = [
            {"$match": {"subscribed_courts": {"$exists": True, "$ne": []}}},
            {"$unwind": "$subscribed_courts"},
            {"$group": {"_id": "$subscribed_courts"}},
        ]
        unique_courts = list(db["user_details"].aggregate(pipeline))

        queued = 0
        for doc in unique_courts:
            court_spec = doc["_id"]
            if not court_spec:
                continue

            if not isinstance(court_spec, dict):
                logger.info(
                    "refresh_subscribed_causelists: skipping legacy subscription without scraper ids: %s",
                    court_spec,
                )
                continue

            high_court_id = str(court_spec.get("high_court_id", "")).strip()
            bench_code = str(court_spec.get("bench_code", "")).strip()
            if not high_court_id or not bench_code:
                logger.info(
                    "refresh_subscribed_causelists: skipping unmapped subscription payload: %s",
                    court_spec,
                )
                continue

            job_id = jm.create_job("system", "causelist_refresh", {
                "court": court_spec, "date": today,
            })
            scrape_cause_list.apply_async(
                kwargs={
                    "job_id": job_id,
                    "date": today,
                    "high_court_id": high_court_id,
                    "bench_code": bench_code,
                    "causelist_type": "daily",
                    "user_id": "system",
                },
                queue="ecourts_background",
            )
            queued += 1

        logger.info("refresh_subscribed_causelists: queued %d cause list scrapes for %s", queued, today)
        return {"queued": queued, "date": today}

    except Exception as e:
        logger.error("refresh_subscribed_causelists failed: %s\n%s", e, traceback.format_exc())
        return {"error": str(e)}


@shared_task(
    name="ecourts_scraper.tasks.refresh_tracked_cases",
    queue="ecourts_background",
    rate_limit="2/m",
)
def refresh_tracked_cases():
    """
    Find all unique CNR numbers across user_details.case_ids,
    then queue re-scrapes for each (skipping recently cached ones).
    """
    from core.init_clients import get_mongo_client
    from ecourts_scraper.cache.cache_manager import EcourtsCacheManager
    from datetime import datetime, timezone, timedelta

    db = get_mongo_client()["legaldb"]
    jm = JobManager()
    cache = EcourtsCacheManager()
    now = datetime.now(timezone.utc)
    min_age = timedelta(hours=12)

    try:
        pipeline = [
            {"$match": {"case_ids": {"$exists": True, "$ne": []}}},
            {"$unwind": "$case_ids"},
            {"$group": {"_id": "$case_ids"}},
        ]
        unique_cnrs = list(db["user_details"].aggregate(pipeline))

        queued = 0
        skipped = 0
        for doc in unique_cnrs:
            cnr = str(doc["_id"]).strip().upper()
            if not cnr or len(cnr) < 10:
                continue

            fresh = False
            for prefix in ("hc:case:", "dc:case:"):
                cached = cache.get(f"{prefix}{cnr}")
                if cached and cached.get("scraped_at"):
                    age = now - cached["scraped_at"]
                    if age < min_age:
                        fresh = True
                        break
            if fresh:
                skipped += 1
                continue

            job_id = jm.create_job("system", "case_refresh_auto", {"cnr": cnr})
            scrape_case_by_cnr.apply_async(
                args=[job_id, cnr, "system"],
                queue="ecourts_background",
            )
            queued += 1

        logger.info("refresh_tracked_cases: queued %d, skipped %d (fresh)", queued, skipped)
        return {"queued": queued, "skipped": skipped}

    except Exception as e:
        logger.error("refresh_tracked_cases failed: %s\n%s", e, traceback.format_exc())
        return {"error": str(e)}


@shared_task(
    name="ecourts_scraper.tasks.health_check_selectors",
    queue="ecourts_background",
)
def health_check_selectors():
    """
    Validate that default selectors still work on target sites.
    Navigates to each site, checks key selectors exist. On failure,
    logs a warning (self-heal can be triggered manually or by the agent).
    """
    from ecourts_scraper.constants import HC_BASE_URL, DC_BASE_URL, HC_SELECTORS, DC_SELECTORS

    results = {"hc": {}, "dc": {}}

    try:
        from ecourts_scraper.infra.browser_pool import browser_pool
        from ecourts_scraper.infra.parsers import element_exists

        context = browser_pool.acquire_context()
        page = browser_pool.new_page(context)

        try:
            page.goto(HC_BASE_URL, wait_until="domcontentloaded", timeout=20000)
            import time
            time.sleep(2)

            for name, sel_info in HC_SELECTORS.items():
                try:
                    found = element_exists(page, sel_info["value"], sel_info["by"], timeout=3000)
                    results["hc"][name] = "ok" if found else "missing"
                except Exception:
                    results["hc"][name] = "error"

            page.goto(DC_BASE_URL, wait_until="domcontentloaded", timeout=20000)
            time.sleep(2)

            for name, sel_info in DC_SELECTORS.items():
                try:
                    found = element_exists(page, sel_info["value"], sel_info["by"], timeout=3000)
                    results["dc"][name] = "ok" if found else "missing"
                except Exception:
                    results["dc"][name] = "error"
        finally:
            browser_pool.release_context(context)

        hc_broken = [k for k, v in results["hc"].items() if v != "ok"]
        dc_broken = [k for k, v in results["dc"].items() if v != "ok"]

        if hc_broken or dc_broken:
            logger.warning(
                "Selector health check found issues -- HC: %s, DC: %s",
                hc_broken or "all ok", dc_broken or "all ok",
            )

        logger.info("Selector health check complete: HC %d ok, DC %d ok",
                     len(results["hc"]) - len(hc_broken),
                     len(results["dc"]) - len(dc_broken))

    except Exception as e:
        logger.error("health_check_selectors failed: %s\n%s", e, traceback.format_exc())
        results["error"] = str(e)

    return results


@shared_task(
    name="ecourts_scraper.tasks.seed_reference_data",
    queue="ecourts_background",
)
def seed_reference_data():
    """
    Materialize stitched-terminal reference datasets into MongoDB so the
    frontend can populate dropdowns without depending on the retired partner
    API warm-cache jobs.
    """
    manager = EcourtsReferenceDataManager()

    seeded = {
        "static": [],
        "district_states": 0,
    }
    try:
        for section in ("case-status", "court-orders", "cause-list", "caveat"):
            doc = manager.get_static_section(section)
            if doc:
                seeded["static"].append(section)

        states_doc = manager.get_district_states()
        seeded["district_states"] = len(states_doc.get("data", []))
        logger.info("seed_reference_data complete: %s", seeded)
        return seeded
    except Exception as e:
        logger.error("seed_reference_data failed: %s\n%s", e, traceback.format_exc())
        return {"error": str(e), **seeded}
