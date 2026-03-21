"""
Deprecated historical Celery tasks for pre-populating direct-API eCourts defaults.

These tasks run on a schedule (via Celery Beat) and store one page of
"latest" results for each eCourts section in MongoDB so that users
see real data when they land on a blank search page without typing anything.

Schedule:
  - Cases & Litigants : daily at 06:30 / 06:35 (court activity resets each day)
  - Lawyers           : weekly on Monday at 06:40 (advocate directory stable)

Storage:
  Uses EcourtsCacheManager with special keys:
    defaults:cases       → search_type=general,  query="petition"
    defaults:litigants   → search_type=litigant, query="state"
    defaults:lawyers     → merged results for 3 advocate name seeds

  These keys are returned by the GET /api/ecourts/defaults/<section>/ endpoint.

Page coverage:
  Only page 1 (20 results) is stored.  Deeper pages are always fetched live
  from the partner API (the frontend will call the search endpoint directly
  when the user paginates beyond the defaults).
"""
import logging
import traceback

from celery import shared_task

from ecourts_api import client, transformers
from ecourts_scraper.cache.cache_manager import EcourtsCacheManager

logger = logging.getLogger("django")

# ── Seed queries ─────────────────────────────────────────────────────────────
# These are broad, always-returning legal terms that give representative
# samples of current eCourts data.
CASE_SEED_QUERY = "civil"          # 'petition' returns 0 from general search param
LITIGANT_SEED_QUERY = "state"
LAWYER_SEED_QUERIES = ["kumar", "sharma", "singh"]

DEFAULT_PAGE_SIZE = 20
DAILY_DEFAULT_TTL_HOURS = 36
WEEKLY_DEFAULT_TTL_HOURS = 8 * 24


# ─────────────────────────────────────────────────────────────────────────────

@shared_task(
    name="ecourts_api.tasks.populate_case_defaults",
    queue="ecourts_background",
    max_retries=2,
    default_retry_delay=300,
)
def populate_case_defaults():
    """
    Populate default case results (page 1) for the Case Search landing page.
    Runs daily. Result stored under cache key ``defaults:cases``.
    """
    try:
        params = {
            "query": CASE_SEED_QUERY,
            "page": 1,
            "pageSize": DEFAULT_PAGE_SIZE,
        }

        raw = client.search(params)
        transformed = transformers.transform_search_results(raw)
        enriched = transformers.enrich_cached_facets(transformed)
        case_list = enriched.get("case_list", [])

        if not case_list:
            logger.warning("[ecourts defaults] cases: empty result set returned — keeping previous cache")
            return {"status": "empty"}

        cache = EcourtsCacheManager()
        cache.set(
            "defaults:cases",
            "ecourts_defaults",
            enriched,
            ttl_hours=DAILY_DEFAULT_TTL_HOURS,
        )

        count = len(case_list)
        logger.info("[ecourts defaults] cases: stored %d results", count)
        return {"status": "ok", "count": count}

    except client.EcourtsApiError as e:
        logger.error("[ecourts defaults] cases API error: %s (code=%s)", e.message, e.code)
        raise

    except Exception:
        logger.error("[ecourts defaults] cases unexpected error:\n%s", traceback.format_exc())
        raise


@shared_task(
    name="ecourts_api.tasks.populate_litigant_defaults",
    queue="ecourts_background",
    max_retries=2,
    default_retry_delay=300,
)
def populate_litigant_defaults():
    """
    Populate default litigant search results (page 1).
    Runs daily. Result stored under cache key ``defaults:litigants``.
    """
    try:
        params = {
            "litigants": LITIGANT_SEED_QUERY,
            "page": 1,
            "pageSize": DEFAULT_PAGE_SIZE,
        }

        raw = client.search(params)
        transformed = transformers.transform_search_results(raw)
        enriched = transformers.enrich_cached_facets(transformed)
        case_list = enriched.get("case_list", [])

        if not case_list:
            logger.warning("[ecourts defaults] litigants: empty result set returned — keeping previous cache")
            return {"status": "empty"}

        cache = EcourtsCacheManager()
        cache.set(
            "defaults:litigants",
            "ecourts_defaults",
            enriched,
            ttl_hours=DAILY_DEFAULT_TTL_HOURS,
        )

        count = len(case_list)
        logger.info("[ecourts defaults] litigants: stored %d results", count)
        return {"status": "ok", "count": count}

    except client.EcourtsApiError as e:
        logger.error("[ecourts defaults] litigants API error: %s (code=%s)", e.message, e.code)
        raise

    except Exception:
        logger.error("[ecourts defaults] litigants unexpected error:\n%s", traceback.format_exc())
        raise


@shared_task(
    name="ecourts_api.tasks.populate_lawyer_defaults",
    queue="ecourts_background",
    max_retries=2,
    default_retry_delay=300,
)
def populate_lawyer_defaults():
    """
    Populate default lawyer search results for the Lawyer Directory landing page.
    Runs weekly (Monday). Merges results from several seed advocate names and
    deduplicates by CNR. Result stored under cache key ``defaults:lawyers``.
    """
    try:
        merged_cases: dict[str, dict] = {}  # cnr -> case dict (dedup by cnr)
        facets = {}

        for seed in LAWYER_SEED_QUERIES:
            try:
                params = {
                    "advocates": seed,
                    "page": 1,
                    "pageSize": DEFAULT_PAGE_SIZE,
                }
                raw = client.search(params)
                transformed = transformers.transform_search_results(raw)
                enriched = transformers.enrich_cached_facets(transformed)

                for case in enriched.get("case_list", []):
                    cnr = case.get("cnr")
                    if cnr and cnr not in merged_cases:
                        merged_cases[cnr] = case

                # Keep facets from the first successful seed
                if not facets:
                    facets = enriched.get("facets", {})

            except client.EcourtsApiError as e:
                logger.warning(
                    "[ecourts defaults] lawyers seed '%s' failed: %s", seed, e.message
                )
            except Exception:
                logger.warning(
                    "[ecourts defaults] lawyers seed '%s' error:\n%s",
                    seed, traceback.format_exc(),
                )

        case_list = list(merged_cases.values())[:DEFAULT_PAGE_SIZE]

        if not case_list:
            logger.warning("[ecourts defaults] lawyers: all seeds returned empty — skipping store")
            return {"status": "empty"}

        result = {
            "case_list": case_list,
            "total": len(case_list),
            "page": 1,
            "page_size": DEFAULT_PAGE_SIZE,
            "total_pages": 1,
            "has_next_page": False,
            "facets": facets,
        }

        cache = EcourtsCacheManager()
        cache.set(
            "defaults:lawyers",
            "ecourts_defaults",
            result,
            ttl_hours=WEEKLY_DEFAULT_TTL_HOURS,
        )

        logger.info("[ecourts defaults] lawyers: stored %d results", len(case_list))
        return {"status": "ok", "count": len(case_list)}

    except Exception:
        logger.error("[ecourts defaults] lawyers unexpected error:\n%s", traceback.format_exc())
        raise
