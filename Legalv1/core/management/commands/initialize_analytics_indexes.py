"""
Management command to initialize MongoDB indexes for analytics collections.

Run: python manage.py initialize_analytics_indexes
"""
from django.core.management.base import BaseCommand
from core.analytics import initialize_usage_events_indexes, initialize_consent_events_indexes
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Initialize MongoDB indexes for analytics (usage_events, consent_events)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Initializing analytics indexes..."))
        
        try:
            # Initialize usage_events indexes
            usage_ok = initialize_usage_events_indexes()
            if usage_ok:
                self.stdout.write(self.style.SUCCESS("✓ usage_events indexes created"))
            else:
                self.stdout.write(self.style.ERROR("✗ Failed to create usage_events indexes"))
            
            # Initialize consent_events indexes
            consent_ok = initialize_consent_events_indexes()
            if consent_ok:
                self.stdout.write(self.style.SUCCESS("✓ consent_events indexes created"))
            else:
                self.stdout.write(self.style.ERROR("✗ Failed to create consent_events indexes"))
            
            if usage_ok and consent_ok:
                self.stdout.write(self.style.SUCCESS("\n✓ All indexes initialized successfully"))
            else:
                self.stdout.write(self.style.WARNING("\n⚠ Some indexes may have failed"))
        
        except Exception as e:
            logger.error(f"[InitAnalyticsIndexes] Error: {e}")
            self.stdout.write(self.style.ERROR(f"\n✗ Error: {e}"))
