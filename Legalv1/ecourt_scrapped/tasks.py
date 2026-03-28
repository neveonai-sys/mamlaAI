"""
Celery tasks for ecourt_scrapped.

crawl_ecourts_full — full hierarchy crawl (states→districts→complexes→…)
                     directly from eCourts; no FastAPI scraper needed.
crawl_ecourts_districts — districts-only crawl for all or specific states.
seed_ecourts_states — instant: writes hardcoded states to MongoDB.
"""

import logging

from celery import shared_task

from ecourt_scrapped.services.ecourts_crawler import (
    STATES,
    ensure_indexes,
    upsert_state,
    scrape_districts,
    upsert_district,
    run_full_crawl,
    read_stats,
)

logger = logging.getLogger("django")


@shared_task(name="ecourt_scrapped.seed_ecourts_states", bind=True)
def seed_ecourts_states(self):
    """Seed all 37 states into ecourts_states. No network calls."""
    ensure_indexes()
    for s in STATES:
        upsert_state(s)
    logger.info(f"[seed_ecourts_states] seeded {len(STATES)} states")
    return {"seeded": len(STATES), "collection": "ecourts_states"}


@shared_task(name="ecourt_scrapped.crawl_ecourts_districts", bind=True,
             soft_time_limit=600, time_limit=660)
def crawl_ecourts_districts(self, state_codes=None):
    """Scrape districts directly from eCourts for all or specific states."""
    ensure_indexes()
    # Ensure states are seeded first
    for s in STATES:
        upsert_state(s)

    targets = ([s for s in STATES if s["code"] in state_codes]
               if state_codes else STATES)

    ok, errors, results = 0, 0, []
    for state in targets:
        try:
            items = scrape_districts(state["code"])
            for d in items:
                upsert_district(state["code"], d)
            ok += 1
            results.append({"state": state["name"], "count": len(items), "status": "ok"})
            logger.info(f"[crawl_districts] {state['name']}: {len(items)} districts")
        except Exception as exc:
            errors += 1
            results.append({"state": state["name"], "status": "error", "error": str(exc)})
            logger.error(f"[crawl_districts] {state['name']}: {exc}")

    return {"ok": ok, "errors": errors, "results": results}


@shared_task(name="ecourt_scrapped.crawl_ecourts_full", bind=True,
             soft_time_limit=14400, time_limit=14460)
def crawl_ecourts_full(self, state_codes=None, dist_codes=None):
    """
    Full hierarchy crawl — states→districts→complexes→establishments
    →courts+police_stations+case_types.

    Directly scrapes eCourts (no FastAPI scraper dependency).
    This can take hours for all India.
    """
    cs = run_full_crawl(
        state_codes=state_codes,
        dist_codes=dist_codes,
    )
    summary = {
        "run_id": cs.run_id,
        "counts": cs.counts,
        "error_count": len(cs.errors),
    }
    logger.info(f"[crawl_ecourts_full] done: {summary}")
    return summary

