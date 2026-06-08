"""
Analytics utilities for recording and querying usage events.

Usage events capture every AI feature call with token counts, costs, and metadata.
These are the foundation for usage-based billing, cost accounting, and feature analytics.
"""
from datetime import datetime
from core.init_clients import get_mongo_db
import logging

logger = logging.getLogger(__name__)


def get_analytics_db():
    return get_mongo_db()


def record_usage_event(request, feature: str, model: str, prompt_tokens: int, completion_tokens: int, metadata: dict = None):
    """
    Record an AI usage event to MongoDB.
    
    Args:
        request: Django request object with telemetry context (request_id, telemetry_user_id, etc.)
        feature: Feature name (e.g., 'ai_draft', 'chat', 'document_analysis')
        model: Model used (e.g., 'gpt-4', 'claude-3-sonnet')
        prompt_tokens: Input token count
        completion_tokens: Output token count
        metadata: Optional additional metadata (context window size, response time, etc.)
    
    Returns:
        Inserted event ID or None if insert failed
    """
    try:
        # Get model pricing
        estimated_cost = calculate_estimated_cost(model, prompt_tokens, completion_tokens)

        # telemetry_user_id is set by middleware before the view decorator runs,
        # so fall back to supabase_user which is available inside the view.
        user_id = getattr(request, "telemetry_user_id", None)
        if not user_id:
            su = getattr(request, "supabase_user", None)
            if su:
                user_id = su.get("user_id") or su.get("sub")

        event = {
            "request_id": getattr(request, "request_id", None),
            "user_id": user_id,
            "session_id": getattr(request, "telemetry_session_id", None),
            "ip_address": getattr(request, "telemetry_client_ip", ""),
            "user_agent": getattr(request, "telemetry_user_agent", ""),
            "feature": feature,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "estimated_cost": estimated_cost,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {},
        }

        db = get_analytics_db()
        result = db.usage_events.insert_one(event)
        
        logger.info(
            "[UsageEvent] feature=%s model=%s tokens=%d cost=%.6f request_id=%s user_id=%s",
            feature,
            model,
            prompt_tokens + completion_tokens,
            estimated_cost,
            event["request_id"],
            event["user_id"] or "anonymous",
        )

        return result.inserted_id
    except Exception as e:
        logger.error("[UsageEvent] Failed to record usage event: %s", e)
        return None


def calculate_estimated_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate estimated provider cost for a usage event.
    
    Pricing tiers (as of June 2026):
    - gpt-4o: $0.005 per 1k input, $0.015 per 1k output
    - gpt-4-turbo: $0.01 per 1k input, $0.03 per 1k output
    - gpt-4: $0.03 per 1k input, $0.06 per 1k output
    - claude-3-5-sonnet: $0.003 per 1k input, $0.015 per 1k output
    - claude-3-opus: $0.015 per 1k input, $0.075 per 1k output
    - gemini-1.5-pro: $0.0035 per 1k input, $0.014 per 1k output
    """
    pricing = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku": {"input": 0.0008, "output": 0.004},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
        "claude-haiku-4-5": {"input": 0.0008, "output": 0.004},
        "gemini-1.5-pro": {"input": 0.0035, "output": 0.014},
        "gemini-1.5-flash": {"input": 0.00035, "output": 0.00105},
    }

    rates = pricing.get(model, {"input": 0.01, "output": 0.03})  # Fallback pricing

    input_cost = (prompt_tokens / 1000.0) * rates["input"]
    output_cost = (completion_tokens / 1000.0) * rates["output"]

    return input_cost + output_cost


def initialize_usage_events_indexes():
    """
    Create indexes on usage_events collection for fast queries.
    Called on app startup or via management command.
    """
    try:
        db = get_analytics_db()
        collection = db.usage_events

        # Index for queries by user_id and timestamp (most common query)
        collection.create_index([("user_id", -1), ("timestamp", -1)], unique=False)
        logger.info("[UsageEvents] Created index on (user_id, timestamp)")

        # Index for queries by feature and timestamp
        collection.create_index([("feature", 1), ("timestamp", -1)], unique=False)
        logger.info("[UsageEvents] Created index on (feature, timestamp)")

        # Index for request tracking
        collection.create_index([("request_id", 1)], unique=False)
        logger.info("[UsageEvents] Created index on request_id")

        logger.info("[UsageEvents] Indexes initialized successfully")
        return True
    except Exception as e:
        logger.error(f"[UsageEvents] Failed to initialize indexes: {e}")
        return False


def initialize_consent_events_indexes():
    """
    Create indexes on consent_events collection for fast queries.
    Called on app startup or via management command.
    """
    try:
        db = get_analytics_db()
        collection = db.consent_events

        # Index for queries by user_id and timestamp
        collection.create_index([("user_id", -1), ("created_at", -1)], unique=False)
        logger.info("[ConsentEvents] Created index on (user_id, created_at)")

        # Index for queries by consent_type
        collection.create_index([("consent_type", 1), ("created_at", -1)], unique=False)
        logger.info("[ConsentEvents] Created index on (consent_type, created_at)")

        logger.info("[ConsentEvents] Indexes initialized successfully")
        return True
    except Exception as e:
        logger.error(f"[ConsentEvents] Failed to initialize indexes: {e}")
        return False
