"""
Management command: check_cost_spikes

Compares today's accumulated provider cost against the 7-day rolling average.
If today's cost exceeds the threshold multiplier, logs a WARNING that can be
caught by any log aggregator (Datadog, CloudWatch, sentry-sdk, etc.).

Usage:
    python manage.py check_cost_spikes              # default: alert if 3× 7-day avg
    python manage.py check_cost_spikes --multiplier 2.0
    python manage.py check_cost_spikes --alert-threshold 0.50  # absolute ₹ / $

Exit codes:
    0 — no spike detected
    1 — spike detected (useful for cron pipelines)
"""
import sys
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from core.init_clients import get_mongo_db


def _day_cost(db, date_str: str) -> float:
    pipeline = [
        {"$match": {
            "timestamp": {
                "$gte": datetime.strptime(date_str, "%Y-%m-%d"),
                "$lt": datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1),
            }
        }},
        {"$group": {"_id": None, "total": {"$sum": "$estimated_cost"}}},
    ]
    result = list(db.usage_events.aggregate(pipeline))
    return result[0]["total"] if result else 0.0


class Command(BaseCommand):
    help = "Check if today's LLM provider cost is spiking versus the 7-day rolling average."

    def add_arguments(self, parser):
        parser.add_argument(
            "--multiplier",
            type=float,
            default=3.0,
            help="Alert if today's cost exceeds this multiple of the 7-day average (default: 3.0).",
        )
        parser.add_argument(
            "--alert-threshold",
            type=float,
            default=0.0,
            help="Also alert if today's cost exceeds this absolute value, regardless of multiplier.",
        )

    def handle(self, *args, **options):
        multiplier = options["multiplier"]
        abs_threshold = options["alert_threshold"]
        db = get_mongo_db()

        today = datetime.utcnow().strftime("%Y-%m-%d")
        today_cost = _day_cost(db, today)

        # 7-day rolling average (excluding today)
        daily_costs = []
        for days_ago in range(1, 8):
            day_str = (datetime.utcnow() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            daily_costs.append(_day_cost(db, day_str))

        avg_7d = sum(daily_costs) / len(daily_costs) if daily_costs else 0.0

        self.stdout.write(
            f"Cost check — today={today_cost:.6f}  7d_avg={avg_7d:.6f}  "
            f"multiplier={multiplier}  abs_threshold={abs_threshold}"
        )

        spike = False

        if avg_7d > 0 and today_cost > avg_7d * multiplier:
            self.stderr.write(
                self.style.ERROR(
                    f"[COST SPIKE] Today's cost ({today_cost:.6f}) is "
                    f"{today_cost / avg_7d:.1f}× the 7-day average ({avg_7d:.6f}). "
                    f"Threshold: {multiplier}×."
                )
            )
            spike = True

        if abs_threshold > 0 and today_cost > abs_threshold:
            self.stderr.write(
                self.style.ERROR(
                    f"[COST SPIKE] Today's cost ({today_cost:.6f}) exceeds the absolute threshold "
                    f"({abs_threshold:.6f})."
                )
            )
            spike = True

        if not spike:
            self.stdout.write(self.style.SUCCESS("No cost spike detected."))

        sys.exit(1 if spike else 0)
