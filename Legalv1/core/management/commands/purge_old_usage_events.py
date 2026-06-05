"""
Management command: purge_old_usage_events

Deletes usage_events documents older than a configurable retention window
(default 730 days / 2 years) to keep the collection lean.

Usage:
    python manage.py purge_old_usage_events              # dry-run, shows count
    python manage.py purge_old_usage_events --execute    # actually deletes
    python manage.py purge_old_usage_events --days 365   # 1-year window
"""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from core.init_clients import get_mongo_db


class Command(BaseCommand):
    help = "Purge usage_events documents older than the retention window (default 730 days)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=730,
            help="Retention window in days (default: 730).",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            default=False,
            help="Actually delete records. Omitting this flag runs a dry-run.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        execute = options["execute"]
        cutoff = datetime.utcnow() - timedelta(days=days)

        db = get_mongo_db()
        query = {"timestamp": {"$lt": cutoff}}

        count = db.usage_events.count_documents(query)

        if not execute:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would delete {count} usage_events older than {days} days "
                    f"(before {cutoff.date()}). Run with --execute to confirm."
                )
            )
            return

        if count == 0:
            self.stdout.write(self.style.SUCCESS("Nothing to purge."))
            return

        result = db.usage_events.delete_many(query)
        self.stdout.write(
            self.style.SUCCESS(
                f"Purged {result.deleted_count} usage_events older than {days} days "
                f"(before {cutoff.date()})."
            )
        )
