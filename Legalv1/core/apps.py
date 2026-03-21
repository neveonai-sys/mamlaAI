from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from supabase import create_client as create_supabase_client, Client as SupabaseClient
from pymongo import MongoClient


def _require_setting(name: str) -> str:
    value = getattr(settings, name, None)
    if isinstance(value, str):
        value = value.strip()
    if not value:
        raise ImproperlyConfigured(
            f"{name} is not configured. Set it in Legalv1/legalenv before starting Django or Celery."
        )
    return value


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    supabase: SupabaseClient = None
    mongo: MongoClient = None

    def ready(self):
        # Initialize Supabase client
        self.supabase = create_supabase_client(
            _require_setting('SUPABASE_URL'),
            _require_setting('SUPABASE_SERVICE_ROLE_KEY')
        )

        # Initialize PyMongo client
        self.mongo = MongoClient(_require_setting('MONGO_URI'))
