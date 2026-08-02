import json
import re
from datetime import timedelta

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from supabase_required import supabase_required
from core.init_clients import get_mongo_db, get_supabase_client
from core.audit_log import (
    audit_from_request,
    ACTION_ADMIN_USER_LOOKUP,
    ACTION_ADMIN_DATA_ACCESS,
    ACTION_PLAN_CHANGED,
)
from core.entitlements import (
    PLAN_FEATURES,
    is_internal_user,
    log_wallet_transaction,
    _collection,
    _wallet_tx_collection,
    _now,
    _template_for_plan,
    _sync_features,
    _next_month_boundary,
)

USER_METADATA_FIELDS = 'user_id, email, first_name, last_name, user_type, phone, created_at'
SORT_FIELDS = {
    'name', 'email', 'user_type', 'joined_at', 'plan_code',
    'wallet_credits_balance', 'tokens_30d', 'requests_30d', 'last_active',
}
NUMERIC_SORT_FIELDS = {'wallet_credits_balance', 'tokens_30d', 'requests_30d'}


def _admin_denied(request):
    """Returns a 403 JsonResponse if the requester isn't an admin, else None."""
    supabase_user = getattr(request, 'supabase_user', None)
    if not supabase_user or not is_internal_user(supabase_user):
        return JsonResponse({'error': 'Admin access required.'}, status=403)
    return None


def _isoformat(value):
    return value.isoformat() if hasattr(value, 'isoformat') else value


def _user_metadata_by_id(user_ids):
    if not user_ids:
        return {}
    resp = get_supabase_client().table('user_metadata').select(USER_METADATA_FIELDS).in_('user_id', user_ids).execute()
    return {row['user_id']: row for row in (resp.data or [])}


def _joined_at(profile, meta):
    return _isoformat(profile.get('onboarding_time') or profile.get('supabase_created_at') or meta.get('created_at'))


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def admin_wallet_top_up(request):
    denied = _admin_denied(request)
    if denied:
        return denied
    supabase_user = request.supabase_user

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    target_email = str(body.get('target_email', '')).strip().lower()
    credits = body.get('credits')
    note = str(body.get('note', '')).strip()
    amount_inr = body.get('amount_inr')

    if not target_email:
        return JsonResponse({'error': 'target_email is required.'}, status=400)
    if not isinstance(credits, int) or credits <= 0:
        return JsonResponse({'error': 'credits must be a positive integer.'}, status=400)

    col = _collection()
    doc = col.find_one({'email': {'$regex': f'^{re.escape(target_email)}$', '$options': 'i'}})
    if not doc:
        return JsonResponse({'error': f'No entitlements found for {target_email}.'}, status=404)

    now = _now()
    col.update_one(
        {'_id': doc['_id']},
        {'$inc': {'wallet_credits_balance': credits}, '$set': {'updated_at': now}},
    )

    log_wallet_transaction(
        doc['user_id'],
        doc['email'],
        'top_up',
        credits,
        amount_inr=amount_inr,
        note=note,
        added_by=supabase_user.get('email', 'admin'),
    )

    updated = col.find_one({'_id': doc['_id']})
    return JsonResponse({
        'success': True,
        'target_email': target_email,
        'credits_added': credits,
        'new_balance': int(updated.get('wallet_credits_balance', 0)),
        'amount_inr': amount_inr,
        'note': note,
    })


@require_http_methods(['GET'])
@supabase_required
def admin_list_users(request):
    denied = _admin_denied(request)
    if denied:
        return denied

    search = request.GET.get('search', '').strip()
    sort_by = request.GET.get('sort_by', 'joined_at')
    if sort_by not in SORT_FIELDS:
        sort_by = 'joined_at'
    sort_dir = request.GET.get('sort_dir', 'desc')
    try:
        page = max(int(request.GET.get('page', 1)), 1)
        page_size = min(max(int(request.GET.get('page_size', 25)), 1), 100)
    except ValueError:
        return JsonResponse({'error': 'page and page_size must be integers.'}, status=400)

    # Name/email/join-date live in Supabase's `user_metadata` table, not Mongo
    # (Mongo `user_details` no longer carries fname/lname/email for current
    # signups) — so that table is the primary source for search + listing.
    meta_query = get_supabase_client().table('user_metadata').select(USER_METADATA_FIELDS)
    if search:
        pattern = f'%{search.replace(",", " ")}%'
        meta_query = meta_query.or_(f'email.ilike.{pattern},first_name.ilike.{pattern},last_name.ilike.{pattern}')
    meta_rows = meta_query.execute().data or []
    user_ids = [m['user_id'] for m in meta_rows if m.get('user_id')]

    db = get_mongo_db()
    details_by_id = {
        d['user_id']: d for d in db['user_details'].find({'user_id': {'$in': user_ids}}, {'password': 0})
    }
    entitlements_by_id = {
        e['user_id']: e for e in _collection().find({'user_id': {'$in': user_ids}})
    }

    cutoff = _now() - timedelta(days=30)
    usage_pipeline = [
        {'$match': {'user_id': {'$in': user_ids}, 'timestamp': {'$gte': cutoff}}},
        {'$group': {
            '_id': '$user_id',
            'requests': {'$sum': 1},
            'tokens': {'$sum': '$total_tokens'},
            'last_used': {'$max': '$timestamp'},
        }},
    ]
    usage_by_id = {row['_id']: row for row in db['usage_events'].aggregate(usage_pipeline)}

    results = []
    for m in meta_rows:
        uid = m.get('user_id')
        det = details_by_id.get(uid, {})
        if det.get('orphaned_signup'):
            # Leftover record from a duplicate signUp() attempt Supabase
            # silently no-op'd — no real auth.users account behind it.
            continue
        ent = entitlements_by_id.get(uid, {})
        usage = usage_by_id.get(uid, {})
        last_used = usage.get('last_used')
        results.append({
            'user_id': uid,
            'email': m.get('email') or det.get('email', ''),
            'name': f"{m.get('first_name') or ''} {m.get('last_name') or ''}".strip(),
            'user_type': m.get('user_type') or det.get('user_type', ''),
            'user_status': det.get('user_status', ''),
            'joined_at': _joined_at(det, m),
            'plan_code': ent.get('plan_code', ''),
            'wallet_credits_balance': int(ent.get('wallet_credits_balance', 0)),
            'tokens_30d': int(usage.get('tokens', 0) or 0),
            'requests_30d': int(usage.get('requests', 0) or 0),
            'last_active': _isoformat(last_used),
        })

    def sort_key(row):
        val = row.get(sort_by)
        return val if sort_by in NUMERIC_SORT_FIELDS else (val or '')

    results.sort(key=sort_key, reverse=(sort_dir != 'asc'))

    total_count = len(results)
    start = (page - 1) * page_size
    page_results = results[start:start + page_size]

    audit_from_request(request, ACTION_ADMIN_USER_LOOKUP)

    return JsonResponse({
        'users': page_results,
        'total_count': total_count,
        'page': page,
        'page_size': page_size,
    })


@require_http_methods(['GET'])
@supabase_required
def admin_get_user_detail(request, user_id):
    denied = _admin_denied(request)
    if denied:
        return denied

    db = get_mongo_db()
    profile = db['user_details'].find_one({'user_id': user_id}, {'password': 0}) or {}
    meta = _user_metadata_by_id([user_id]).get(user_id, {})
    if not profile and not meta:
        return JsonResponse({'error': 'User not found.'}, status=404)

    entitlements_doc = _collection().find_one({'user_id': user_id}) or {}
    wallet_tx = list(
        _wallet_tx_collection()
        .find({'user_id': user_id}, {'_id': 0})
        .sort('created_at', -1)
        .limit(20)
    )

    cutoff = _now() - timedelta(days=30)
    usage_pipeline = [
        {'$match': {'user_id': user_id, 'timestamp': {'$gte': cutoff}}},
        {'$group': {
            '_id': '$user_id',
            'requests': {'$sum': 1},
            'tokens': {'$sum': '$total_tokens'},
            'last_used': {'$max': '$timestamp'},
        }},
    ]
    usage_rows = list(db['usage_events'].aggregate(usage_pipeline))
    usage = usage_rows[0] if usage_rows else {}
    last_used = usage.get('last_used')

    audit_from_request(request, ACTION_ADMIN_DATA_ACCESS, target_id=user_id)

    return JsonResponse({
        'profile': {
            'user_id': user_id,
            'email': meta.get('email') or profile.get('email', ''),
            'name': f"{meta.get('first_name') or ''} {meta.get('last_name') or ''}".strip(),
            'user_type': meta.get('user_type') or profile.get('user_type', ''),
            'user_status': profile.get('user_status', ''),
            'phone_number': profile.get('phone_number') or meta.get('phone') or '',
            'joined_at': _joined_at(profile, meta),
        },
        'plan_code': entitlements_doc.get('plan_code', ''),
        'wallet_credits_balance': int(entitlements_doc.get('wallet_credits_balance', 0)),
        'features': entitlements_doc.get('features', {}),
        'wallet_transactions': [
            {**tx, 'created_at': _isoformat(tx.get('created_at'))}
            for tx in wallet_tx
        ],
        'usage_30d': {
            'requests': int(usage.get('requests', 0) or 0),
            'tokens': int(usage.get('tokens', 0) or 0),
            'last_used': _isoformat(last_used),
        },
    })


@csrf_exempt
@require_http_methods(['POST'])
@supabase_required
def admin_update_user_package(request, user_id):
    denied = _admin_denied(request)
    if denied:
        return denied
    supabase_user = request.supabase_user

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    plan_code = str(body.get('plan_code', '')).strip()
    if plan_code not in PLAN_FEATURES:
        return JsonResponse({'error': f'Unknown plan_code: {plan_code}'}, status=400)

    col = _collection()
    doc = col.find_one({'user_id': user_id})
    now = _now()

    if not doc:
        # Plenty of users (Clients especially) never triggered the lazy
        # entitlements-doc creation that normally happens on first AI-feature
        # use — an admin must still be able to assign them a package.
        meta = _user_metadata_by_id([user_id]).get(user_id, {})
        profile = get_mongo_db()['user_details'].find_one({'user_id': user_id}) or {}
        if not meta and not profile:
            return JsonResponse({'error': f'User {user_id} not found.'}, status=404)
        doc = {
            'user_id': user_id,
            'email': meta.get('email') or profile.get('email', ''),
            'user_type': meta.get('user_type') or profile.get('user_type', ''),
            'wallet_credits_balance': 0,
            'currency_code': 'INR',
            'features': {},
            'created_at': now,
        }

    old_plan = doc.get('plan_code', '')
    template = _template_for_plan(plan_code)
    synced_features = _sync_features(doc.get('features'), template)
    col.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'plan_code': plan_code,
                'features': synced_features,
                'updated_at': now,
                'email': doc.get('email', ''),
                'user_type': doc.get('user_type', ''),
            },
            '$setOnInsert': {
                'wallet_credits_balance': 0,
                'currency_code': 'INR',
                'launch_access': 'lawyers_only',
                'trial_started_at': None,
                'trial_ends_at': None,
                'billing_cycle_anchor': now,
                'quota_reset_at': _next_month_boundary(now),
                'created_at': now,
            },
        },
        upsert=True,
    )

    audit_from_request(
        request, ACTION_PLAN_CHANGED, target_id=user_id,
        metadata={'old_plan': old_plan, 'new_plan': plan_code, 'changed_by': supabase_user.get('email', '')},
    )

    updated = col.find_one({'user_id': user_id})
    return JsonResponse({
        'success': True,
        'user_id': user_id,
        'old_plan': old_plan,
        'new_plan': plan_code,
        'features': updated.get('features', {}),
    })
