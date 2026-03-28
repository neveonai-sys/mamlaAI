"""
Management command: seed_ecourts_hierarchy

Crawls the full eCourts location hierarchy directly from the eCourts website
(using curl_cffi for TLS impersonation) and stores it in separate MongoDB
collections per entity type.

Collections written:
    ecourts_states, ecourts_districts, ecourts_complexes,
    ecourts_establishments, ecourts_courts, ecourts_police_stations,
    ecourts_case_types, ecourts_crawl_log

Usage:
    # Seed states only (fast, hardcoded, no network calls):
    python manage.py seed_ecourts_hierarchy

    # Full crawl — all states → districts → complexes → establishments
    # → courts + police stations + case types (HOURS for all India):
    python manage.py seed_ecourts_hierarchy --full

    # Crawl only specific states (comma-separated codes):
    python manage.py seed_ecourts_hierarchy --full --state-codes 8,26

    # Crawl specific districts within a single state:
    python manage.py seed_ecourts_hierarchy --full --state-codes 8 --dist-codes 34,42

    # Districts only (no deep establishment-level crawl):
    python manage.py seed_ecourts_hierarchy --districts

    # Districts for specific states:
    python manage.py seed_ecourts_hierarchy --districts --state-codes 8,26

    # Show current data statistics:
    python manage.py seed_ecourts_hierarchy --stats
"""

from django.core.management.base import BaseCommand

from ecourt_scrapped.services.ecourts_crawler import (
    STATES,
    ensure_indexes,
    upsert_state,
    scrape_districts,
    upsert_district,
    run_full_crawl,
    read_stats,
)


class Command(BaseCommand):
    help = (
        "Seed eCourts location hierarchy into MongoDB. "
        "States are hardcoded; everything else is scraped directly from eCourts."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--full", action="store_true", default=False,
            help="Full crawl: states→districts→complexes→establishments→courts/PS/caseTypes",
        )
        parser.add_argument(
            "--districts", action="store_true", default=False,
            help="Seed states + scrape districts only (no deeper crawl)",
        )
        parser.add_argument(
            "--state-codes", type=str, default="",
            help="Comma-separated state codes to limit the crawl (default: all)",
        )
        parser.add_argument(
            "--dist-codes", type=str, default="",
            help="Comma-separated district codes (only meaningful with a single --state-codes)",
        )
        parser.add_argument(
            "--stats", action="store_true", default=False,
            help="Print collection counts and last crawl info, then exit",
        )

    def handle(self, *args, **options):
        if options["stats"]:
            stats = read_stats()
            self.stdout.write(self.style.SUCCESS("Collection counts:"))
            for name, count in stats["collections"].items():
                self.stdout.write(f"  {name}: {count}")
            last = stats.get("last_crawl") or {}
            if last:
                self.stdout.write(f"\nLast crawl: status={last.get('status')} "
                                  f"started={last.get('started_at')} "
                                  f"finished={last.get('finished_at')}")
                if last.get("counts"):
                    for k, v in last["counts"].items():
                        self.stdout.write(f"    {k}: {v}")
            return

        state_filter = set(
            s.strip() for s in options["state_codes"].split(",") if s.strip()
        )
        dist_filter = set(
            s.strip() for s in options["dist_codes"].split(",") if s.strip()
        )

        # Always seed states first (instant, no network)
        ensure_indexes()
        for s in STATES:
            upsert_state(s)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(STATES)} states into ecourts_states."
        ))

        do_full = options["full"]
        do_districts = options["districts"]

        if not do_full and not do_districts:
            self.stdout.write(
                "Run with --districts for district-only seeding, "
                "or --full for the complete hierarchy crawl."
            )
            return

        # Districts-only mode
        if do_districts and not do_full:
            targets = [s for s in STATES
                       if not state_filter or s["code"] in state_filter]
            ok, errs = 0, 0
            for state in targets:
                try:
                    items = scrape_districts(state["code"])
                    for d in items:
                        upsert_district(state["code"], d)
                    ok += 1
                    self.stdout.write(
                        f"  {state['name']}: {len(items)} districts"
                    )
                except Exception as e:
                    errs += 1
                    self.stderr.write(self.style.ERROR(
                        f"  ERROR {state['name']}: {e}"
                    ))
            self.stdout.write(self.style.SUCCESS(
                f"\nDistrict seeding done: {ok} states OK, {errs} errors."
            ))
            return

        # Full crawl
        self.stdout.write(self.style.WARNING(
            "Starting FULL hierarchy crawl (this can take hours)..."
        ))
        cs = run_full_crawl(
            state_codes=list(state_filter) if state_filter else None,
            dist_codes=list(dist_filter) if dist_filter else None,
        )
        self.stdout.write(self.style.SUCCESS(
            f"\nCrawl {cs.run_id} finished."
        ))
        for k, v in cs.counts.items():
            self.stdout.write(f"  {k}: {v}")
        if cs.errors:
            self.stdout.write(self.style.WARNING(
                f"\n{len(cs.errors)} errors occurred. Check ecourts_crawl_log."
            ))

