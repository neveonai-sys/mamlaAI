"""
Management command: anonymize_expired_payment_records

Anonymises payment_orders / payment_transactions documents older than the
retention window (default 2555 days / 7 years), per the Privacy Policy's
Data Retention table: "Payment records — 7 years — Tax/audit compliance
(Income Tax Act)."

This ANONYMISES (strips the identifying/linkable fields: user_id and the
Razorpay order/payment/signature references) rather than hard-deletes.
Unlike usage_events, a silent unconditional TTL-index delete on financial
records risks destroying a row still needed for an active tax audit or
chargeback dispute — anonymising keeps amount/currency/status/plan/date
intact for audit continuity without retaining anything that identifies who
paid.

Note: the `billing` app (Legalv1/billing/) is currently DORMANT — not wired
into INSTALLED_APPS or urls.py (see billing/models.py docstring) — so these
collections likely hold no live production data yet. This command is
forward-looking: it's a no-op today and becomes load-bearing the moment
billing is activated.

Usage:
    python manage.py anonymize_expired_payment_records              # dry-run
    python manage.py anonymize_expired_payment_records --execute    # actually anonymises
    python manage.py anonymize_expired_payment_records --days 1825  # 5-year window
"""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from core.init_clients import get_mongo_db
from core.audit_log import ACTION_PAYMENT_RECORD_ANONYMIZED, write_audit_log

_ANONYMISED_MARKER = "anonymised"

# Per-collection identifying fields to scrub, matching each collection's
# actual schema (billing/models.py new_payment_order / new_payment_transaction)
# — payment_orders never has razorpay_payment_id/signature, so we don't
# fabricate those fields on it.
_COLLECTION_FIELDS = {
    "payment_orders": ("user_id", "razorpay_order_id"),
    "payment_transactions": ("user_id", "order_id", "razorpay_order_id", "razorpay_payment_id", "razorpay_signature"),
}
_COLLECTIONS = tuple(_COLLECTION_FIELDS.keys())


class Command(BaseCommand):
    help = "Anonymise payment_orders/payment_transactions older than the retention window (default 2555 days / 7 years)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=2555,
            help="Retention window in days (default: 2555 / 7 years).",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            default=False,
            help="Actually anonymise records. Omitting this flag runs a dry-run.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        execute = options["execute"]
        cutoff = datetime.utcnow() - timedelta(days=days)

        db = get_mongo_db()
        query = {"created_at": {"$lt": cutoff}, "user_id": {"$ne": _ANONYMISED_MARKER}}

        total_matched = 0
        for collection_name in _COLLECTIONS:
            count = db[collection_name].count_documents(query)
            total_matched += count
            if not execute:
                self.stdout.write(
                    f"[DRY RUN] {collection_name}: {count} record(s) older than {days} days "
                    f"(before {cutoff.date()}) would be anonymised."
                )

        if not execute:
            self.stdout.write(self.style.WARNING(
                f"Total: {total_matched} record(s) would be anonymised. Run with --execute to confirm."
            ))
            return

        if total_matched == 0:
            self.stdout.write(self.style.SUCCESS("Nothing to anonymise."))
            return

        for collection_name in _COLLECTIONS:
            update_fields = {field: _ANONYMISED_MARKER for field in _COLLECTION_FIELDS[collection_name]}
            update_fields["payment_data_anonymised_at"] = datetime.utcnow()
            result = db[collection_name].update_many(query, {"$set": update_fields})
            write_audit_log(
                ACTION_PAYMENT_RECORD_ANONYMIZED,
                actor_id="system",
                target_id=collection_name,
                metadata={"collection": collection_name, "records_anonymised": result.modified_count, "retention_days": days},
            )
            self.stdout.write(self.style.SUCCESS(
                f"Anonymised {result.modified_count} record(s) in {collection_name} older than {days} days."
            ))
