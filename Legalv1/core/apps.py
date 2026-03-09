from django.apps import AppConfig
from django.conf import settings
from supabase import create_client as create_supabase_client, Client as SupabaseClient
from pymongo import MongoClient


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    supabase: SupabaseClient = None
    mongo: MongoClient = None

    def ready(self):
        # Initialize Supabase client
        self.supabase = create_supabase_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

        # Initialize PyMongo client
        self.mongo = MongoClient(settings.MONGO_URI)
