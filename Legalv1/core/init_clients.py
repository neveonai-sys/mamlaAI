from typing import Optional
from django.apps import apps
from core.apps import CoreConfig
from supabase import Client as SupabaseClient
from pymongo import MongoClient, IndexModel
from pymongo.errors import ConnectionFailure
from opensearchpy import OpenSearch, RequestsHttpConnection
from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured
import logging
import os
from django.conf import settings
logger = logging.getLogger('django')

class DatabaseClients:
    _instance = None
    _mongo_client = None
    _opensearch_client = None
    _redis_cache = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseClients, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._mongo_client = None
        self._opensearch_client = None
        self._redis_cache = None

    def init_clients(self):
        """Initialize all database clients with connection pooling"""
        self._init_mongo_client()
        self._init_redis_cache()

    def _init_mongo_client(self):
        """Initialize MongoDB client with connection pooling"""
        try:
            mongo_uri = (settings.MONGO_URI or '').strip()
            if not mongo_uri:
                raise ImproperlyConfigured(
                    "MONGO_URI is not configured. Set MONGO_URI or the MONGO_HOSTNAME/MONGO_PWD/MONGO_APPNAME trio in Legalv1/legalenv."
                )
            self._mongo_client = MongoClient(
                mongo_uri,
                maxPoolSize=100,       # Maximum connections in the pool
                minPoolSize=0,         # Don't hold idle connections — Atlas closes them anyway,
                                       # triggering AutoReconnect noise in the background thread.
                                       # PyMongo reconnects on demand with no user impact.
                maxIdleTimeMS=25000,   # Close our idle connections after 25 s — *before* Atlas's
                                       # idle-connection timeout fires (typically 30–60 s on Atlas).
                                       # Prevents the race where Atlas closes first and PyMongo's
                                       # pool maintenance logs spurious AutoReconnect errors.
                connectTimeoutMS=10000,          # Fail fast if can't open a new connection
                socketTimeoutMS=30000,           # Wait up to 30 s for a query response
                serverSelectionTimeoutMS=5000,   # Give up server selection after 5 s
                heartbeatFrequencyMS=30000,      # Topology heartbeat interval (default 10 s → 30 s
                                                 # reduces connection churn against Atlas).
                retryWrites=True,
                retryReads=True,
            )
            # Test the connection
            self._mongo_client.admin.command('ping')
            logger.info("MongoDB connection established successfully")
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise

    def _init_redis_cache(self):
        """Initialize Redis cache client"""
        try:
            self._redis_cache = caches['default']
            # Test the connection
            self._redis_cache.set('connection_test', 'success', timeout=5)
            if self._redis_cache.get('connection_test') != 'success':
                raise ConnectionError("Redis cache test failed")
            logger.info("Redis cache connection established successfully")
        except Exception as e:
            logger.error(f"Redis cache connection failed: {e}")
            # Fall back to local memory cache if Redis is not available
            self._redis_cache = caches['local']
            logger.warning("Falling back to local memory cache")

    @property
    def mongo(self) -> MongoClient:
        if not self._mongo_client:
            self._init_mongo_client()
        return self._mongo_client

    @property
    def cache(self):
        if not self._redis_cache:
            self._init_redis_cache()
        return self._redis_cache

# Initialize the singleton instance
db_clients = DatabaseClients()

def get_supabase_client() -> SupabaseClient:
    """Get Supabase client with connection pooling"""
    core_config: CoreConfig = apps.get_app_config('core')
    return core_config.supabase

def get_mongo_client() -> MongoClient:
    """Get MongoDB client with connection pooling"""
    return db_clients.mongo

def get_mongo_db():
    """Get the configured MongoDB database (respects MONGO_DB_NAME env var)"""
    from django.conf import settings
    return db_clients.mongo[settings.MONGO_DB_NAME]

def ensure_indexes():
    """Create necessary database indexes"""
    try:
        from django.conf import settings
        db = db_clients.mongo[settings.MONGO_DB_NAME]
        
        # List of supported languages
        SUPPORTED_LANGUAGES = {
            'English': 'en',
            'Hindi': 'hi',
            'Bengali': 'bn',
            'Telugu': 'te',
            'Marathi': 'mr',
            'Tamil': 'ta',
            'Urdu': 'ur',
            'Gujarati': 'gu',
            'Kannada': 'kn',
            'Malayalam': 'ml',
            'Odia': 'or',
            'Punjabi': 'pa',
            'Assamese': 'as'
        }

        # def normalize_language(lang):
        #     """Convert language name to ISO code and handle case variations"""
        #     lang = lang.lower()
        #     for full_name, iso_code in SUPPORTED_LANGUAGES.items():
        #         if lang == full_name.lower() or lang == iso_code.lower():
        #             return iso_code
        #     return 'en'  # Default to English if language not found

        # User details indexes
        user_details = db.user_details
        existing_user_indexes = user_details.index_information()
        if "user_id" not in existing_user_indexes:
            user_details.create_index([("user_id", 1)])
        if "email" not in existing_user_indexes:
            user_details.create_index([("email", 1)])
        if "phone" not in existing_user_indexes:
            user_details.create_index([("phone", 1)])
        if "created_at" not in existing_user_indexes:
            user_details.create_index([("created_at", -1)])
        
        # Draft content indexes
        draft_content = db.draft_content_data
        existing_draft_indexes = draft_content.index_information()
        if "draft_type" not in existing_draft_indexes:
            draft_content.create_index([("draft_type", 1), ("filename", 1)])
        
        # Update existing documents with unsupported language values
        # for lang in SUPPORTED_LANGUAGES.values():
        #     draft_content.update_many(
        #         {"language": {"$in": [lang, lang.upper(), lang.lower()]}},
        #         {"$set": {"language": lang}}
        #     )
        
        # if "keywords_text_index" not in existing_draft_indexes:
        #     # Create text index with language support
        #     draft_content.create_index([
        #         ("keywords", "text")
        #     ], name="keywords_text_index", default_language="en")
        
        if "created_at" not in existing_draft_indexes:
            draft_content.create_index([("created_at", -1)])
        
        # AI drafts indexes
        aidrafts = db.aidrafts_complete_data
        existing_aidrafts_indexes = aidrafts.index_information()
        
        # Update existing documents with unsupported language values
        # for lang in SUPPORTED_LANGUAGES.values():
        #     aidrafts.update_many(
        #         {"language": {"$in": [lang, lang.upper(), lang.lower()]}},
        #         {"$set": {"language": lang}}
        #     )
        
        if "user_id" not in existing_aidrafts_indexes:
            aidrafts.create_index([("user_id", 1)])
        if "session_id" not in existing_aidrafts_indexes:
            aidrafts.create_index([("session_id", 1)])
        if "created_at" not in existing_aidrafts_indexes:
            aidrafts.create_index([("created_at", -1)])
        
        if "draft_name_text_index" not in existing_aidrafts_indexes:
            # Create text index with language support
            aidrafts.create_index([
                ("draft_name", "text")
            ], name="draft_name_text_index")

        # Cases app indexes
        db["cases"].create_index([("lawyer_id", 1), ("status", 1)])
        db["cases"].create_index([("client_ids", 1)])
        db["cases"].create_index([("cnr", 1)])
        db["cases"].create_index([("case_ref", 1)], unique=True)
        db["hearing_notes"].create_index([("case_id", 1), ("hearing_date", -1)])
        db["case_notes"].create_index([("case_id", 1), ("created_at", -1)])
        db["case_notes"].create_index([("case_id", 1), ("visibility", 1)])
        db["case_tasks"].create_index([("case_id", 1), ("status", 1)])
        db["case_tasks"].create_index([("assigned_to", 1), ("due_date", 1)])

        # MamlaAI Chat (v2) usage-summary aggregation index
        db["brain_v2_messages"].create_index([("owner_id", 1), ("role", 1)])

        logger.info("Database indexes created/verified successfully")
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")
        logger.error(f"Error details: {str(e)}")
        raise

# Initialize clients when module is imported
try:
    db_clients.init_clients()
    # ensure_indexes()
except Exception as e:
    logger.error(f"Failed to initialize database clients: {e}", exc_info=True)
    logger.error(f"Error details: {str(e)}")
    raise
