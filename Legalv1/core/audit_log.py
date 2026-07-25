"""
Audit log service.

Writes structured records to the MongoDB `audit_logs` collection for any
privileged or irreversible action: data deletion, plan changes, admin reads,
authentication events, and sensitive data access.

Schema per document:
    action        str      — machine-readable action code, e.g. "user_login"
    actor_id      str      — user_id of the person who triggered the action
    actor_type    str      — user_type / role of the actor
    target_id     str      — user_id / resource id being acted on (if different)
    session_id    str      — login session that produced this action
    metadata      dict     — free-form action details (no PII values)
    ip_address    str
    user_agent    str
    timestamp     datetime (UTC)
"""
import logging
from datetime import datetime

from core.init_clients import get_mongo_db

logger = logging.getLogger(__name__)

_AUDIT_COLLECTION = "audit_logs"

# ── Action constants (use these to avoid free-text typos) ────────────────────

# Authentication
ACTION_USER_LOGIN = "user_login"
ACTION_USER_LOGOUT = "user_logout"
ACTION_LOGIN_FAILED = "login_failed"
ACTION_PASSWORD_RESET_REQUESTED = "password_reset_requested"
ACTION_EMAIL_CHANGED = "email_changed"
ACTION_PHONE_CHANGED = "phone_changed"

# Data subject / privacy
ACTION_DELETE_USER_DATA = "delete_user_data"
ACTION_EXPORT_USER_DATA = "export_user_data"
ACTION_CONSENT_CHANGED = "consent_changed"

# Case and document operations
ACTION_CASE_CREATED = "case_created"
ACTION_CASE_DELETED = "case_deleted"
ACTION_CASE_ACCESSED = "case_accessed"
ACTION_DOCUMENT_UPLOADED = "document_uploaded"
ACTION_DOCUMENT_DOWNLOADED = "document_downloaded"
ACTION_DOCUMENT_DELETED = "document_deleted"

# AI / draft operations
ACTION_AI_DRAFT_GENERATED = "ai_draft_generated"
ACTION_AI_DRAFT_EXPORTED = "ai_draft_exported"

# Billing
ACTION_PLAN_CHANGED = "plan_changed"
ACTION_SUBSCRIPTION_CANCELLED = "subscription_cancelled"

# Admin
ACTION_ADMIN_DATA_ACCESS = "admin_data_access"
ACTION_ADMIN_USER_LOOKUP = "admin_user_lookup"
ACTION_ANALYTICS_READ = "analytics_usage_by_user_read"
ACTION_OWNER_DASHBOARD_READ = "owner_dashboard_read"

# Scheduled retention / compliance jobs
ACTION_CASE_DATA_PURGED = "case_data_purged"
ACTION_PAYMENT_RECORD_ANONYMIZED = "payment_record_anonymized"


def write_audit_log(
    action: str,
    actor_id: str,
    *,
    actor_type: str = "",
    target_id: str = "",
    session_id: str = "",
    metadata: dict | None = None,
    ip_address: str = "",
    user_agent: str = "",
) -> None:
    """Insert one audit record. Never raises — errors are logged and swallowed."""
    try:
        db = get_mongo_db()
        db[_AUDIT_COLLECTION].insert_one(
            {
                "action": action,
                "actor_id": actor_id,
                "actor_type": actor_type,
                "target_id": target_id or actor_id,
                "session_id": session_id,
                "metadata": metadata or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
                "timestamp": datetime.utcnow(),
            }
        )
    except Exception as exc:
        logger.error("[AuditLog] Failed to write audit record action=%s: %s", action, exc)


def audit_from_request(request, action: str, *, target_id: str = "", metadata: dict | None = None) -> None:
    """Convenience wrapper that extracts actor info directly from a Django request."""
    user = getattr(request, "supabase_user", None) or {}
    actor_id = user.get("user_id", "")
    actor_type = user.get("user_type", "")
    # Use proxy-aware IP set by TelemetryMiddleware when available
    ip_address = getattr(request, "telemetry_client_ip", None) or request.META.get("REMOTE_ADDR", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    session_id = getattr(request, "telemetry_session_id", "") or ""
    write_audit_log(
        action,
        actor_id,
        actor_type=actor_type,
        target_id=target_id or actor_id,
        session_id=session_id,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )
