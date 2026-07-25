"""
Scheduled compliance/retention tasks.

Each task wraps a management command via call_command rather than
duplicating the delete/anonymise logic here, so there's a single
implementation usable both from Celery beat (scheduled) and manually from
the shell (ops/debugging) with the same --days/--execute flags.
"""
from celery import shared_task
from django.core.management import call_command


@shared_task
def purge_old_usage_events_task():
    call_command('purge_old_usage_events', execute=True)


@shared_task
def purge_expired_case_data_task():
    call_command('purge_expired_case_data', execute=True)


@shared_task
def anonymize_expired_payment_records_task():
    call_command('anonymize_expired_payment_records', execute=True)
