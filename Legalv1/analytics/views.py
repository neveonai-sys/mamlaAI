"""
Analytics API endpoints for querying usage data.

Exposes:
- /api/analytics/usage/summary — total usage across all users
- /api/analytics/usage/by-user — breakdown by user
- /api/analytics/usage/by-feature — breakdown by feature
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
from core.init_clients import get_mongo_db
from core.audit_log import audit_from_request

from supabase_required import supabase_required
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_analytics_db():
    return get_mongo_db()


def _is_owner(request):
    """Allow owner/admin user_type OR any email listed in BRAIN_ADMIN_EMAILS."""
    user = getattr(request, "supabase_user", None)
    if not user:
        return False
    if user.get("user_type") in ("owner", "admin"):
        return True
    admin_emails = [
        e.strip()
        for e in str(getattr(settings, "BRAIN_ADMIN_EMAILS", "") or "").split(",")
        if e.strip()
    ]
    return user.get("email", "") in admin_emails


@api_view(["GET"])
@supabase_required
def usage_summary(request):
    """
    Get overall usage summary.
    
    Query params:
    - days: Number of days to look back (default: 30)
    - feature: Filter by feature name (optional)
    
    Returns:
    {
        "total_requests": int,
        "total_tokens": int,
        "total_cost": float,
        "by_model": {model: {requests, tokens, cost}},
        "daily_breakdown": [{date, requests, tokens, cost}]
    }
    """
    if not _is_owner(request):
        return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

    try:
        days = int(request.GET.get("days", 30))
        feature_filter = request.GET.get("feature", None)
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        db = get_analytics_db()
        collection = db.usage_events
        
        # Build query
        query = {"timestamp": {"$gte": cutoff_date}}
        if feature_filter:
            query["feature"] = feature_filter
        
        # Get all events in the period
        events = list(collection.find(query))
        
        if not events:
            return Response({
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "by_model": {},
                "daily_breakdown": [],
                "period_days": days,
            })
        
        # Aggregate stats
        total_requests = len(events)
        total_tokens = sum(e.get("total_tokens", 0) for e in events)
        total_cost = sum(e.get("estimated_cost", 0) for e in events)
        
        # By model breakdown
        by_model = {}
        for event in events:
            model = event.get("model", "unknown")
            if model not in by_model:
                by_model[model] = {"requests": 0, "tokens": 0, "cost": 0}
            by_model[model]["requests"] += 1
            by_model[model]["tokens"] += event.get("total_tokens", 0)
            by_model[model]["cost"] += event.get("estimated_cost", 0)
        
        # Daily breakdown
        daily_breakdown = {}
        for event in events:
            date_key = event.get("timestamp", datetime.utcnow()).strftime("%Y-%m-%d")
            if date_key not in daily_breakdown:
                daily_breakdown[date_key] = {"requests": 0, "tokens": 0, "cost": 0}
            daily_breakdown[date_key]["requests"] += 1
            daily_breakdown[date_key]["tokens"] += event.get("total_tokens", 0)
            daily_breakdown[date_key]["cost"] += event.get("estimated_cost", 0)
        
        daily_list = [{"date": k, **v} for k, v in sorted(daily_breakdown.items())]
        
        return Response({
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
            "by_model": by_model,
            "daily_breakdown": daily_list,
            "period_days": days,
        })
    
    except Exception as e:
        logger.error(f"[UsageSummary] Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@supabase_required
def usage_by_user(request):
    """
    Get usage breakdown by user (owner/user/admin only).
    
    Query params:
    - days: Number of days (default: 30)
    - limit: Max users to return (default: 50)
    
    Returns:
    {
        "users": [
            {user_id, requests, tokens, cost, last_used},
            ...
        ]
    }
    """
    if not _is_owner(request):
        return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

    audit_from_request(request, "analytics_usage_by_user_read")

    try:
        days = int(request.GET.get("days", 30))
        limit = int(request.GET.get("limit", 50))
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        db = get_analytics_db()
        collection = db.usage_events
        
        # Aggregate by user
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_date}, "user_id": {"$ne": None}}},
            {"$group": {
                "_id": "$user_id",
                "requests": {"$sum": 1},
                "tokens": {"$sum": "$total_tokens"},
                "cost": {"$sum": "$estimated_cost"},
                "last_used": {"$max": "$timestamp"}
            }},
            {"$sort": {"cost": -1}},
            {"$limit": limit},
        ]
        
        users = list(collection.aggregate(pipeline))
        
        # Reformat response
        user_list = [
            {
                "user_id": u["_id"],
                "requests": u["requests"],
                "tokens": u["tokens"],
                "cost": round(u["cost"], 6),
                "last_used": u["last_used"].isoformat() if u.get("last_used") else None,
            }
            for u in users
        ]
        
        return Response({
            "users": user_list,
            "period_days": days,
            "count": len(user_list),
        })
    
    except Exception as e:
        logger.error(f"[UsageByUser] Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@supabase_required
def usage_by_feature(request):
    """
    Get usage breakdown by feature.
    
    Query params:
    - days: Number of days (default: 30)
    
    Returns:
    {
        "features": [
            {feature, requests, tokens, cost, users_count},
            ...
        ]
    }
    """
    if not _is_owner(request):
        return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

    try:
        days = int(request.GET.get("days", 30))

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        db = get_analytics_db()
        collection = db.usage_events
        
        # Aggregate by feature
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_date}}},
            {"$group": {
                "_id": "$feature",
                "requests": {"$sum": 1},
                "tokens": {"$sum": "$total_tokens"},
                "cost": {"$sum": "$estimated_cost"},
                "unique_users": {"$addToSet": "$user_id"}
            }},
            {"$sort": {"cost": -1}},
        ]
        
        features = list(collection.aggregate(pipeline))
        
        # Reformat response
        feature_list = [
            {
                "feature": f["_id"],
                "requests": f["requests"],
                "tokens": f["tokens"],
                "cost": round(f["cost"], 6),
                "unique_users": len([u for u in f.get("unique_users", []) if u]),  # Count non-null
            }
            for f in features
        ]
        
        return Response({
            "features": feature_list,
            "period_days": days,
        })
    
    except Exception as e:
        logger.error(f"[UsageByFeature] Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@supabase_required
def owner_dashboard(request):
    """
    Owner summary dashboard — DAU/MAU, feature adoption, token costs, daily P&L.
    GET /api/analytics/owner/dashboard/?days=30

    Returns aggregated metrics for the owner.
    Restricted to owner/admin user types.
    """
    if not _is_owner(request):
        return Response({"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

    audit_from_request(request, "owner_dashboard_read")

    try:
        days = int(request.GET.get("days", 30))
        cutoff = datetime.utcnow() - timedelta(days=days)
        today_cutoff = datetime.utcnow() - timedelta(days=1)

        db = get_analytics_db()

        # --- DAU: distinct users in last 24 h ---
        dau_pipeline = [
            {"$match": {"timestamp": {"$gte": today_cutoff}, "user_id": {"$ne": None}}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "dau"},
        ]
        dau_result = list(db.usage_events.aggregate(dau_pipeline))
        dau = dau_result[0]["dau"] if dau_result else 0

        # --- MAU: distinct users in last 30 days ---
        mau_cutoff = datetime.utcnow() - timedelta(days=30)
        mau_pipeline = [
            {"$match": {"timestamp": {"$gte": mau_cutoff}, "user_id": {"$ne": None}}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "mau"},
        ]
        mau_result = list(db.usage_events.aggregate(mau_pipeline))
        mau = mau_result[0]["mau"] if mau_result else 0

        # --- Token cost summary for the period ---
        cost_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "total_tokens": {"$sum": "$total_tokens"},
                "total_cost": {"$sum": "$estimated_cost"},
            }},
        ]
        cost_result = list(db.usage_events.aggregate(cost_pipeline))
        cost_agg = cost_result[0] if cost_result else {"total_requests": 0, "total_tokens": 0, "total_cost": 0}

        # --- Feature adoption: top features by unique users ---
        adoption_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$feature",
                "requests": {"$sum": 1},
                "unique_users": {"$addToSet": "$user_id"},
                "cost": {"$sum": "$estimated_cost"},
            }},
            {"$sort": {"requests": -1}},
        ]
        adoption = [
            {
                "feature": f["_id"],
                "requests": f["requests"],
                "unique_users": len([u for u in f.get("unique_users", []) if u]),
                "cost": round(f["cost"], 6),
            }
            for f in db.usage_events.aggregate(adoption_pipeline)
        ]

        # --- Daily cost breakdown ---
        daily_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "requests": {"$sum": 1},
                "tokens": {"$sum": "$total_tokens"},
                "cost": {"$sum": "$estimated_cost"},
                "unique_users": {"$addToSet": "$user_id"},
            }},
            {"$sort": {"_id": 1}},
        ]
        daily = [
            {
                "date": d["_id"],
                "requests": d["requests"],
                "tokens": d["tokens"],
                "cost": round(d["cost"], 6),
                "active_users": len([u for u in d.get("unique_users", []) if u]),
            }
            for d in db.usage_events.aggregate(daily_pipeline)
        ]

        return Response({
            "period_days": days,
            "dau": dau,
            "mau": mau,
            "total_requests": cost_agg.get("total_requests", 0),
            "total_tokens": cost_agg.get("total_tokens", 0),
            "total_provider_cost": round(cost_agg.get("total_cost", 0), 6),
            "feature_adoption": adoption,
            "daily_breakdown": daily,
        })

    except Exception as e:
        logger.error(f"[OwnerDashboard] Error: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
