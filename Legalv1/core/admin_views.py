import json
import re

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.entitlements import (
    is_internal_user,
    log_wallet_transaction,
    _collection,
    _now,
)


@csrf_exempt
@require_http_methods(['POST'])
def admin_wallet_top_up(request):
    supabase_user = getattr(request, 'supabase_user', None)
    if not supabase_user or not is_internal_user(supabase_user):
        return JsonResponse({'error': 'Admin access required.'}, status=403)

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
