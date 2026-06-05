"""
Audit log service.

Writes structured records to the MongoDB `audit_logs` collection for any
privileged or irreversible action: data deletion, plan changes, admin reads.

Schema per document:
    action        str   — machine-readable action code, e.g. "delete_user_data"
    actor_id      str   — user_id of the person who triggered the action
    actor_type    str   — user_type / role of the actor
    target_id     str   — user_id / resource id being acted on (if different)
    metadata      dict  — free-form action details (no PII values)
    ip_address    str
    user_agent    str
    timestamp     datetime
"""
import logging
from datetime import datetime

from core.init_clients import get_mongo_db

logger = logging.getLogger("django")

_AUDIT_COLLECTION = "audit_logs"


def write_audit_log(
    action: str,
    actor_id: str,
    *,
    actor_type: str = "",
    target_id: str = "",
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
    ip_address = request.META.get("REMOTE_ADDR", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    write_audit_log(
        action,
        actor_id,
        actor_type=actor_type,
        target_id=target_id or actor_id,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )
