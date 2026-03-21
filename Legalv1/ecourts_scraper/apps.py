from django.apps import AppConfig


class EcourtsScraperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ecourts_scraper'

    def ready(self):
        try:
            from ecourts_scraper.cache.collections import ensure_ecourts_indexes

            ensure_ecourts_indexes()
        except Exception:
            # Startup must stay resilient even if Mongo is temporarily unavailable.
            pass
