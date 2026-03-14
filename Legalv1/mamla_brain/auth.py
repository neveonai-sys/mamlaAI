import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

from django.conf import settings
from django.http import JsonResponse

from core.init_clients import get_mongo_client
from supabase_required import verify_supabase_token


def _db():
    return get_mongo_client()['legaldb']


def _now():
    return datetime.utcnow()


def _next_month_boundary(reference=None):
    current = reference or _now()
    first_of_month = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (first_of_month + timedelta(days=32)).replace(day=1)
    return next_month


def _hash_key(raw_key):
    return hashlib.sha256(raw_key.encode('utf-8')).hexdigest()


def is_supabase_admin(supabase_user):
    if not supabase_user:
        return False

    admin_flags = ('is_admin', 'admin', 'is_superuser')
    for flag in admin_flags:
        if supabase_user.get(flag) is True:
            return True

    for role_key in ('role', 'user_role', 'account_type', 'user_type'):
        role_value = str(supabase_user.get(role_key, '')).strip().lower()
        if role_value in {'admin', 'superadmin', 'owner'}:
            return True

    configured_emails = {
        email.strip().lower()
        for email in str(getattr(settings, 'BRAIN_ADMIN_EMAILS', '') or '').split(',')
        if email.strip()
    }
    email = str(supabase_user.get('email', '')).strip().lower()
    return bool(email and email in configured_emails)


def generate_api_key(owner_name, owner_email, plan='free', scopes=None, quota_monthly=None):
    raw_key = f'mbk_live_{secrets.token_urlsafe(24)}'
    key_prefix = raw_key[:16]
    document = {
        'key_hash': _hash_key(raw_key),
        'key_prefix': key_prefix,
        'owner_id': f'brain_api:{key_prefix}',
        'owner_name': owner_name,
        'owner_email': owner_email,
        'plan': plan,
        'quota_monthly': quota_monthly or getattr(settings, 'BRAIN_MONTHLY_FREE_QUOTA', 100),
        'quota_used': 0,
        'quota_reset_at': _next_month_boundary(),
        'scopes': scopes or ['doc_qa'],
        'created_at': _now(),
        'last_used_at': None,
        'active': True,
    }
    result = _db()['brain_api_keys'].insert_one(document)
    document['_id'] = result.inserted_id
    document['raw_key'] = raw_key
    return document


def _load_supabase_user(request):
    access_token = request.COOKIES.get('access_token')
    if not access_token:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            if auth_header.lower().startswith('bearer '):
                access_token = auth_header[7:].strip()
            else:
                access_token = auth_header.strip()
    if not access_token:
        return None
    return verify_supabase_token(access_token)


def _reset_quota_if_due(api_key_doc):
    quota_reset_at = api_key_doc.get('quota_reset_at')
    if quota_reset_at and quota_reset_at > _now():
        return api_key_doc

    updated_reset_at = _next_month_boundary()
    _db()['brain_api_keys'].update_one(
        {'_id': api_key_doc['_id']},
        {'$set': {'quota_used': 0, 'quota_reset_at': updated_reset_at}},
    )
    api_key_doc['quota_used'] = 0
    api_key_doc['quota_reset_at'] = updated_reset_at
    return api_key_doc


def _load_api_key_client(request):
    raw_key = request.headers.get('X-Brain-API-Key', '').strip()
    if not raw_key:
        return None

    api_key_doc = _db()['brain_api_keys'].find_one({'key_hash': _hash_key(raw_key), 'active': True})
    if not api_key_doc:
        return JsonResponse({'error': 'invalid_api_key'}, status=401)

    api_key_doc = _reset_quota_if_due(api_key_doc)
    if api_key_doc.get('quota_used', 0) >= api_key_doc.get('quota_monthly', 0):
        return JsonResponse({'error': 'quota_exceeded'}, status=429)

    request.brain_client = {
        'auth_type': 'api_key',
        'api_key_id': str(api_key_doc['_id']),
        'owner_id': api_key_doc.get('owner_id') or f"brain_api:{api_key_doc.get('key_prefix')}",
        'owner_name': api_key_doc.get('owner_name', ''),
        'owner_email': api_key_doc.get('owner_email', ''),
        'plan': api_key_doc.get('plan', 'free'),
        'scopes': api_key_doc.get('scopes', []),
        'key_prefix': api_key_doc.get('key_prefix', ''),
    }
    request.brain_api_key_document = api_key_doc
    return None


def _charge_api_key_quota(request):
    api_key_doc = getattr(request, 'brain_api_key_document', None)
    if not api_key_doc:
        return
    _db()['brain_api_keys'].update_one(
        {'_id': api_key_doc['_id']},
        {'$inc': {'quota_used': 1}, '$set': {'last_used_at': _now()}},
    )


def charge_brain_api_key_quota(request, units=1):
    api_key_doc = getattr(request, 'brain_api_key_document', None)
    if not api_key_doc or units <= 0:
        return None

    _db()['brain_api_keys'].update_one(
        {'_id': api_key_doc['_id']},
        {'$inc': {'quota_used': units}, '$set': {'last_used_at': _now()}},
    )
    api_key_doc['quota_used'] = api_key_doc.get('quota_used', 0) + units
    api_key_doc['last_used_at'] = _now()
    request.brain_quota_handled = True
    return api_key_doc


def brain_api_key_quota_payload(request, feature_code, *, allowed=True, next_cta='continue', message_key='', wallet_credits_charged=0):
    api_key_doc = getattr(request, 'brain_api_key_document', None)
    quota_monthly = int((api_key_doc or {}).get('quota_monthly', 0))
    quota_used = int((api_key_doc or {}).get('quota_used', 0))
    return {
        'feature_code': feature_code,
        'allowed': allowed,
        'plan_code': (api_key_doc or {}).get('plan', 'free'),
        'is_trial': False,
        'launch_access': 'general',
        'used_count': quota_used,
        'included_limit': quota_monthly,
        'remaining_included': max(quota_monthly - quota_used, 0),
        'wallet_credits_balance': 0,
        'wallet_credits_charged': wallet_credits_charged,
        'quota_reset_at': str((api_key_doc or {}).get('quota_reset_at', '')),
        'next_cta': next_cta,
        'message_key': message_key,
    }


def brain_api_key_required(view_func=None, *, scopes=None):
    required_scopes = scopes or []

    def decorator(func):
        @wraps(func)
        def wrapped(request, *args, **kwargs):
            try:
                supabase_user = _load_supabase_user(request)
            except Exception:
                supabase_user = None

            if supabase_user:
                request.supabase_user = supabase_user
                request.brain_client = {
                    'auth_type': 'supabase',
                    'owner_id': supabase_user.get('user_id'),
                    'owner_email': supabase_user.get('email', ''),
                    'owner_name': supabase_user.get('full_name') or supabase_user.get('name') or '',
                    'scopes': ['*'],
                    'plan': 'internal',
                }
            else:
                api_key_error = _load_api_key_client(request)
                if api_key_error is not None:
                    return api_key_error

            if not getattr(request, 'brain_client', None):
                return JsonResponse({'error': 'authentication_required'}, status=401)

            caller_scopes = set(request.brain_client.get('scopes', []))
            if required_scopes and '*' not in caller_scopes and not set(required_scopes).issubset(caller_scopes):
                return JsonResponse({'error': 'insufficient_scope', 'required_scopes': required_scopes}, status=403)

            response = func(request, *args, **kwargs)
            if (
                request.brain_client.get('auth_type') == 'api_key'
                and getattr(response, 'status_code', 200) < 400
                and not getattr(request, 'brain_quota_handled', False)
            ):
                _charge_api_key_quota(request)
            return response

        return wrapped

    if view_func is not None:
        return decorator(view_func)
    return decorator
