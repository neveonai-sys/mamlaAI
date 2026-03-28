from django.apps import AppConfig


class EcourtScrappedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ecourt_scrapped'
    verbose_name = 'eCourts Scrapped (FastAPI proxy)'
