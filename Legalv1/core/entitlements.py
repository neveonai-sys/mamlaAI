from copy import deepcopy
from datetime import datetime, timedelta

from django.conf import settings

from core.init_clients import get_mongo_client, get_mongo_db


FEATURE_ORDER = (
    'brain_doc_analysis',
    'general_legal_chat',
    'brain_drafting_actions',
    'case_companion',
    'ai_suggestions',
    'ai_draft_generation',
    'ecourts_case_lookup',
    'ecourts_order_download',
)


PLAN_FEATURES = {
    # ── Trial (new user default — 30 days) ──────────────────────────────────
    # eCourts served by ecourt_scrapped v2 (FastAPI proxy) — cost is compute only.
    'trial': {
        'brain_doc_analysis':     {'included_limit': 8,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 24, 'soft_warning_threshold': 0.80, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 12, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'case_companion':         {'included_limit': 2,  'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 5,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 20, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 50, 'soft_warning_threshold': 0.80, 'overage_credit_cost': 1, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 5,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': False},
    },
    # ── Vakil Starter ₹299/month ─────────────────────────────────────────────
    'vakil_starter': {
        'brain_doc_analysis':     {'included_limit': 15, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 50, 'soft_warning_threshold': 0.80, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 20, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'case_companion':         {'included_limit': 3,  'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 10, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 30, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 60, 'soft_warning_threshold': 0.80, 'overage_credit_cost': 1, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 15, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': False},
    },
    # ── Vakil Pro ₹699/month ─────────────────────────────────────────────────
    'vakil_pro': {
        'brain_doc_analysis':     {'included_limit': 40,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 150,     'soft_warning_threshold': 0.85, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 60,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'case_companion':         {'included_limit': 10,      'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 25,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 70,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 50,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': False},
    },
    # ── Vakil Power ₹1,299/month ─────────────────────────────────────────────
    'vakil_power': {
        'brain_doc_analysis':     {'included_limit': 100,     'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 400,     'soft_warning_threshold': 0.85, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 150,     'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'case_companion':         {'included_limit': 30,      'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 75,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 150,     'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 150,     'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': False},
    },
    # ── Nagrik Free (trial-style expiry — citizen plan, lawyer features hard-blocked)
    'nagrik_free': {
        'brain_doc_analysis':     {'included_limit': 2,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 5,  'soft_warning_threshold': 0.80, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 0,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': True},   # lawyer-only
        'case_companion':         {'included_limit': 0,  'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': True},   # lawyer-only
        'ai_suggestions':         {'included_limit': 0,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': True},   # lawyer-only
        'ai_draft_generation':    {'included_limit': 1,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 10, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 0,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': True},
    },
    # ── Nagrik Basic ₹79/month (citizen plan, lawyer features hard-blocked) ──
    'nagrik_basic': {
        'brain_doc_analysis':     {'included_limit': 8,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 30, 'soft_warning_threshold': 0.80, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 0,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': True},   # lawyer-only
        'case_companion':         {'included_limit': 0,  'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': True},   # lawyer-only
        'ai_suggestions':         {'included_limit': 0,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': True},   # lawyer-only
        'ai_draft_generation':    {'included_limit': 5,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 30, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 3,  'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': False},
    },
    # ── Firm Basic ₹1,999/month (= Vakil Pro quotas per seat) ───────────────
    'firm_basic': {
        'brain_doc_analysis':     {'included_limit': 40,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 150,     'soft_warning_threshold': 0.85, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 60,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'case_companion':         {'included_limit': 10,      'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 25,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 70,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 50,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': False},
    },
    # ── Firm Pro ₹4,499/month (= Vakil Power quotas per seat) ───────────────
    'firm_pro': {
        'brain_doc_analysis':     {'included_limit': 100,     'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 400,     'soft_warning_threshold': 0.85, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 150,     'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'case_companion':         {'included_limit': 30,      'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 75,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 150,     'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 150,     'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': False},
    },
    # ── Pro (legacy plan code — kept for backward compatibility) ────────────
    'pro': {
        'brain_doc_analysis':     {'included_limit': 30,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 120,     'soft_warning_threshold': 0.85, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 40,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'case_companion':         {'included_limit': 8,       'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 20,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 60,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 40,      'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': False},
    },
    # ── Enterprise / Internal (unlimited) ───────────────────────────────────
    'enterprise': {
        'brain_doc_analysis':     {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 1000000, 'soft_warning_threshold': 0.98, 'overage_credit_cost': 0, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'case_companion':         {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
    },
    'internal': {
        'brain_doc_analysis':     {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 1000000, 'soft_warning_threshold': 0.98, 'overage_credit_cost': 0, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'case_companion':         {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 1000000, 'soft_warning_threshold': 0.95, 'overage_credit_cost': 0, 'hard_block': False},
    },
    # ── Locked (trial expired — wallet credits still usable as soft grace) ──
    'locked': {
        'brain_doc_analysis':     {'included_limit': 0, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'general_legal_chat':     {'included_limit': 0, 'soft_warning_threshold': 0.80, 'overage_credit_cost': 1, 'hard_block': False},
        'brain_drafting_actions': {'included_limit': 0, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 2, 'hard_block': False},
        'case_companion':         {'included_limit': 0, 'soft_warning_threshold': 0.50, 'overage_credit_cost': 5, 'hard_block': False},
        'ai_suggestions':         {'included_limit': 0, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ai_draft_generation':    {'included_limit': 0, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 4, 'hard_block': False},
        'ecourts_case_lookup':    {'included_limit': 0, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 1, 'hard_block': False},
        'ecourts_order_download': {'included_limit': 0, 'soft_warning_threshold': 0.75, 'overage_credit_cost': 3, 'hard_block': False},
    },
}

# Plans that don't expire in Phase A (active paid subscriptions).
# In Phase B, subscription status from the `subscriptions` MongoDB collection will replace this set.
PAID_PLANS = {
    'pro', 'vakil_starter', 'vakil_pro', 'vakil_power',
    'nagrik_basic', 'firm_basic', 'firm_pro',
}


def _db():
    return get_mongo_db()


def _collection():
    return _db()['user_ai_entitlements']


def _now():
    return datetime.utcnow()


def _next_month_boundary(reference=None):
    current = reference or _now()
    first_of_month = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (first_of_month + timedelta(days=32)).replace(day=1)


def _trial_end(reference=None):
    return (reference or _now()) + timedelta(days=30)


def _lower(value):
    return str(value or '').strip().lower()


def is_internal_user(supabase_user):
    if not supabase_user:
        return False

    for flag in ('is_admin', 'admin', 'is_superuser'):
        if supabase_user.get(flag) is True:
            return True

    for role_key in ('role', 'user_role', 'account_type', 'user_type'):
        if _lower(supabase_user.get(role_key)) in {'admin', 'superadmin', 'owner', 'internal'}:
            return True

    configured_emails = {
        email.strip().lower()
        for email in str(getattr(settings, 'BRAIN_ADMIN_EMAILS', '') or '').split(',')
        if email.strip()
    }
    email = _lower(supabase_user.get('email'))
    return bool(email and email in configured_emails)


def _default_launch_access(supabase_user):
    if is_internal_user(supabase_user):
        return 'internal_only'
    return 'lawyers_only'


def _base_plan_code(supabase_user):
    if is_internal_user(supabase_user):
        return 'internal'
    return 'trial'


def _effective_plan_code(document, current_time=None):
    if not document:
        return 'trial'

    current = current_time or _now()
    plan_code = _lower(document.get('plan_code')) or 'trial'
    if plan_code == 'internal':
        return 'internal'
    if plan_code == 'enterprise':
        return 'enterprise'
    # Paid plans never expire in Phase A — no trial_ends_at check needed
    if plan_code in PAID_PLANS:
        return plan_code

    trial_ends_at = document.get('trial_ends_at')
    if trial_ends_at and trial_ends_at > current:
        return 'trial'
    return 'locked'


def _template_for_plan(plan_code):
    return deepcopy(PLAN_FEATURES.get(plan_code, PLAN_FEATURES['locked']))


def _sync_features(existing_features, template):
    synced = {}
    existing_features = existing_features or {}
    for feature_code in FEATURE_ORDER:
        feature_template = template.get(feature_code, {})
        existing = existing_features.get(feature_code, {})
        synced[feature_code] = {
            'included_limit': int(feature_template.get('included_limit', 0)),
            'used_count': int(existing.get('used_count', 0)),
            'soft_warning_threshold': float(feature_template.get('soft_warning_threshold', 0.75)),
            'overage_credit_cost': int(feature_template.get('overage_credit_cost', 0)),
            'hard_block': bool(feature_template.get('hard_block', False)),
            'overage_used_count': int(existing.get('overage_used_count', 0)),
            'last_used_at': existing.get('last_used_at'),
        }
    return synced


def _launch_allowed(supabase_user, launch_access):
    if is_internal_user(supabase_user):
        return True
    if launch_access == 'general':
        return True
    if launch_access == 'lawyers_only':
        return _lower(supabase_user.get('user_type')) == 'lawyer'
    if launch_access == 'internal_only':
        return False
    return False


def ensure_user_entitlements(supabase_user):
    current = _now()
    user_id = supabase_user.get('user_id')
    document = _collection().find_one({'user_id': user_id})

    if not document:
        base_plan = _base_plan_code(supabase_user)
        template = _template_for_plan(base_plan)
        document = {
            'user_id': user_id,
            'email': supabase_user.get('email', ''),
            'user_type': supabase_user.get('user_type', ''),
            'plan_code': base_plan,
            'launch_access': _default_launch_access(supabase_user),
            'trial_started_at': current,
            'trial_ends_at': _trial_end(current) if base_plan == 'trial' else None,
            'billing_cycle_anchor': current,
            'quota_reset_at': _next_month_boundary(current),
            'wallet_credits_balance': 0,
            'currency_code': 'INR',
            'features': _sync_features({}, template),
            'last_activity_at': current,
            'created_at': current,
            'updated_at': current,
        }
        _collection().insert_one(document)
        return document

    updates = {}
    reset_needed = document.get('quota_reset_at') and document['quota_reset_at'] <= current
    if reset_needed:
        reset_features = {}
        for feature_code, feature_state in (document.get('features') or {}).items():
            reset_features[feature_code] = {
                **feature_state,
                'used_count': 0,
                'overage_used_count': 0,
            }
        updates['features'] = reset_features
        updates['quota_reset_at'] = _next_month_boundary(current)

    effective_plan_code = _effective_plan_code(document, current)
    template = _template_for_plan(effective_plan_code)
    synced_features = _sync_features(updates.get('features') or document.get('features'), template)
    if synced_features != document.get('features'):
        updates['features'] = synced_features

    if document.get('email') != supabase_user.get('email', ''):
        updates['email'] = supabase_user.get('email', '')
    if document.get('user_type') != supabase_user.get('user_type', ''):
        updates['user_type'] = supabase_user.get('user_type', '')
    # Auto-promote to internal plan if the email is now in BRAIN_ADMIN_EMAILS.
    # Runs on every request so it takes effect immediately after the env var is set,
    # even for users whose MongoDB document was created before the var existed.
    if is_internal_user(supabase_user) and document.get('plan_code') != 'internal':
        updates['plan_code'] = 'internal'
        updates['launch_access'] = 'internal_only'

    if updates:
        updates['updated_at'] = current
        _collection().update_one({'_id': document['_id']}, {'$set': updates})
        document.update(updates)

    return document


def _feature_payload(document, feature_code, *, allowed=True, next_cta='', message_key='', wallet_credits_charged=0):
    current = _now()
    effective_plan_code = _effective_plan_code(document, current)
    feature = (document.get('features') or {}).get(feature_code, {})
    included_limit = int(feature.get('included_limit', 0))
    used_count = int(feature.get('used_count', 0))
    remaining = max(included_limit - used_count, 0)
    trial_ends_at = document.get('trial_ends_at')
    is_trial = bool(effective_plan_code == 'trial' and trial_ends_at and trial_ends_at > current)
    return {
        'feature_code': feature_code,
        'allowed': allowed,
        'plan_code': effective_plan_code,
        'is_trial': is_trial,
        'launch_access': document.get('launch_access', 'lawyers_only'),
        'used_count': used_count,
        'included_limit': included_limit,
        'remaining_included': remaining,
        'wallet_credits_balance': int(document.get('wallet_credits_balance', 0)),
        'wallet_credits_charged': int(wallet_credits_charged),
        'quota_reset_at': str(document.get('quota_reset_at', '')),
        'next_cta': next_cta,
        'message_key': message_key,
        'soft_warning_threshold': feature.get('soft_warning_threshold', 0.75),
        'overage_credit_cost': int(feature.get('overage_credit_cost', 0)),
        'hard_block': bool(feature.get('hard_block', False)),
    }


def get_feature_quota_payload(
    supabase_user,
    feature_code,
    *,
    allowed=True,
    next_cta='',
    message_key='',
    wallet_credits_charged=0,
    included_limit_override=None,
    used_count_override=None,
    remaining_override=None,
):
    document = ensure_user_entitlements(supabase_user)
    payload = _feature_payload(
        document,
        feature_code,
        allowed=allowed,
        next_cta=next_cta,
        message_key=message_key,
        wallet_credits_charged=wallet_credits_charged,
    )
    if included_limit_override is not None:
        payload['included_limit'] = int(included_limit_override)
    if used_count_override is not None:
        payload['used_count'] = int(used_count_override)
    if remaining_override is not None:
        payload['remaining_included'] = int(remaining_override)
    elif included_limit_override is not None and used_count_override is not None:
        payload['remaining_included'] = max(int(included_limit_override) - int(used_count_override), 0)
    return payload


def get_entitlement_summary(supabase_user):
    document = ensure_user_entitlements(supabase_user)
    current = _now()
    effective_plan_code = _effective_plan_code(document, current)
    trial_ends_at = document.get('trial_ends_at')
    return {
        'plan_code': effective_plan_code,
        'launch_access': document.get('launch_access', 'lawyers_only'),
        'wallet': {
            'balance': int(document.get('wallet_credits_balance', 0)),
            'currency_code': document.get('currency_code', 'INR'),
        },
        'trial': {
            'active': bool(effective_plan_code == 'trial' and trial_ends_at and trial_ends_at > current),
            'started_at': str(document.get('trial_started_at', '')),
            'ends_at': str(trial_ends_at or ''),
            'days_remaining': max((trial_ends_at - current).days, 0) if (trial_ends_at and trial_ends_at > current) else 0,
        },
        'quota_reset_at': str(document.get('quota_reset_at', '')),
        'features': {
            feature_code: _feature_payload(document, feature_code)
            for feature_code in FEATURE_ORDER
        },
    }


def authorize_feature_use(supabase_user, feature_code):
    document = ensure_user_entitlements(supabase_user)

    # Dev bypass — never block in local development (DEBUG=True)
    if getattr(settings, 'DEBUG', False):
        quota = _feature_payload(document, feature_code, next_cta='continue', message_key='dev_mode_bypass')
        return {
            'allowed': True,
            'charge_source': 'included',
            'wallet_credits_charged': 0,
            'quota': quota,
        }

    if not _launch_allowed(supabase_user, document.get('launch_access', 'lawyers_only')):
        quota = _feature_payload(
            document,
            feature_code,
            allowed=False,
            next_cta='not_available_yet',
            message_key='launch_restricted',
        )
        return {
            'allowed': False,
            'status_code': 403,
            'message': 'Mamla Brain is being rolled out gradually.',
            'quota': quota,
        }

    feature = (document.get('features') or {}).get(feature_code)
    if not feature:
        quota = _feature_payload(
            document,
            feature_code,
            allowed=False,
            next_cta='upgrade_plan',
            message_key='feature_not_in_plan',
        )
        return {
            'allowed': False,
            'status_code': 403,
            'message': 'This feature is not available in your current plan.',
            'quota': quota,
        }

    included_limit = int(feature.get('included_limit', 0))
    used_count = int(feature.get('used_count', 0))
    remaining = max(included_limit - used_count, 0)
    overage_credit_cost = int(feature.get('overage_credit_cost', 0))
    wallet_balance = int(document.get('wallet_credits_balance', 0))
    hard_block = bool(feature.get('hard_block', False))

    if remaining > 0:
        message_key = ''
        usage_ratio = (used_count + 1) / included_limit if included_limit else 1
        if included_limit and usage_ratio >= float(feature.get('soft_warning_threshold', 0.75)):
            message_key = 'trial_active_low_remaining' if _effective_plan_code(document) == 'trial' else 'quota_low_remaining'
        quota = _feature_payload(document, feature_code, next_cta='continue', message_key=message_key)
        return {
            'allowed': True,
            'charge_source': 'included',
            'wallet_credits_charged': 0,
            'quota': quota,
        }

    if hard_block:
        quota = _feature_payload(
            document,
            feature_code,
            allowed=False,
            next_cta='upgrade_plan',
            message_key='feature_not_in_plan',
        )
        return {
            'allowed': False,
            'status_code': 403,
            'message': 'This feature is not available in your current plan.',
            'quota': quota,
        }

    if overage_credit_cost > 0 and wallet_balance >= overage_credit_cost:
        quota = _feature_payload(
            document,
            feature_code,
            next_cta='use_credits',
            message_key='included_quota_exhausted_wallet_available',
        )
        return {
            'allowed': True,
            'charge_source': 'wallet',
            'wallet_credits_charged': overage_credit_cost,
            'quota': quota,
        }

    next_cta = 'upgrade_plan' if _effective_plan_code(document) == 'trial' else 'top_up_credits'
    quota = _feature_payload(
        document,
        feature_code,
        allowed=False,
        next_cta=next_cta,
        message_key='included_quota_exhausted_upgrade_required',
    )
    return {
        'allowed': False,
        'status_code': 429,
        'message': 'Included usage is exhausted for this feature.',
        'quota': quota,
    }


def consume_feature_use(supabase_user, feature_code, decision):
    document = ensure_user_entitlements(supabase_user)
    # Dev bypass — do NOT increment counters or deduct wallet in local development (DEBUG=True)
    if getattr(settings, 'DEBUG', False):
        return _feature_payload(document, feature_code, allowed=True, next_cta='continue', message_key='dev_mode_bypass')
    feature = (document.get('features') or {}).get(feature_code, {})
    charge_source = decision.get('charge_source', 'included')
    wallet_credits_charged = int(decision.get('wallet_credits_charged', 0))
    current = _now()

    inc_payload = {
        f'features.{feature_code}.used_count': 1,
    }
    if charge_source == 'wallet' and wallet_credits_charged > 0:
        inc_payload[f'features.{feature_code}.overage_used_count'] = 1
        inc_payload['wallet_credits_balance'] = -wallet_credits_charged

    _collection().update_one(
        {'_id': document['_id']},
        {
            '$inc': inc_payload,
            '$set': {
                f'features.{feature_code}.last_used_at': current,
                'last_activity_at': current,
                'updated_at': current,
            },
        },
    )

    updated = ensure_user_entitlements(supabase_user)
    message_key = decision.get('quota', {}).get('message_key', '')
    if charge_source == 'wallet' and wallet_credits_charged > 0:
        message_key = 'success_wallet_charged'
    return _feature_payload(
        updated,
        feature_code,
        allowed=True,
        next_cta='continue',
        message_key=message_key,
        wallet_credits_charged=wallet_credits_charged,
    )