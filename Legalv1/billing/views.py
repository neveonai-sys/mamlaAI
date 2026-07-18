"""
Billing views — Razorpay integration.

DORMANT — not active until payment gateway is subscribed.
See billing/models.py for activation instructions.
"""
import hashlib
import hmac
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from core.init_clients import get_mongo_db
from supabase_required import supabase_required
from .models import new_payment_order, new_payment_transaction, new_subscription, new_invoice

logger = logging.getLogger('django')


PLAN_PRICES_PAISE = {
    'law_student':   22000,
    'basic':        100000,
    'premium':      300000,
    'vakil_starter': 34900,
    'vakil_pro':     74900,
    'vakil_power':  134900,
    'nagrik_basic':  12900,
    'nagrik_pro':    24900,
    'firm_basic':   204900,
    'firm_pro':     454900,
}


def _razorpay_client():
    import razorpay
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _db():
    return get_mongo_db()


@api_view(['POST'])
@supabase_required
def create_order(request):
    """
    Create a Razorpay order for a plan upgrade.
    POST /api/billing/create-order/
    Body: {"plan_id": "vakil_pro"}
    """
    try:
        plan_id = (request.data.get('plan_id') or '').strip()
        if plan_id not in PLAN_PRICES_PAISE:
            return Response({'error': f'Unknown plan: {plan_id}'}, status=status.HTTP_400_BAD_REQUEST)

        user_id = request.supabase_user.get('user_id')
        amount = PLAN_PRICES_PAISE[plan_id]

        client = _razorpay_client()
        rz_order = client.order.create({
            'amount': amount,
            'currency': 'INR',
            'receipt': f'order_{user_id}_{plan_id}',
        })

        order = new_payment_order(user_id, plan_id, amount)
        order['razorpay_order_id'] = rz_order['id']
        _db().payment_orders.insert_one(order)

        return Response({
            'order_id': rz_order['id'],
            'amount': amount,
            'currency': 'INR',
            'key': settings.RAZORPAY_KEY_ID,
        })
    except Exception as e:
        logger.error('[Billing] create_order error: %s', e)
        return Response({'error': 'Order creation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@supabase_required
def verify_payment(request):
    """
    Verify payment signature after Razorpay checkout completes.
    POST /api/billing/verify-payment/
    Body: {razorpay_order_id, razorpay_payment_id, razorpay_signature, plan_id}
    """
    try:
        data = request.data
        rz_order_id = data.get('razorpay_order_id', '')
        rz_payment_id = data.get('razorpay_payment_id', '')
        rz_signature = data.get('razorpay_signature', '')
        plan_id = data.get('plan_id', '')
        user_id = request.supabase_user.get('user_id')

        expected = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f'{rz_order_id}|{rz_payment_id}'.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, rz_signature):
            return Response({'error': 'Invalid payment signature'}, status=status.HTTP_400_BAD_REQUEST)

        db = _db()

        order_doc = db.payment_orders.find_one({'razorpay_order_id': rz_order_id})
        if not order_doc:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        txn = new_payment_transaction(
            user_id=user_id,
            order_id=str(order_doc['_id']),
            razorpay_payment_id=rz_payment_id,
            razorpay_order_id=rz_order_id,
            razorpay_signature=rz_signature,
            amount_paise=order_doc['amount_paise'],
        )
        db.payment_transactions.insert_one(txn)

        db.payment_orders.update_one({'razorpay_order_id': rz_order_id}, {'$set': {'status': 'captured', 'updated_at': datetime.utcnow()}})

        period_start = datetime.utcnow()
        period_end = period_start + timedelta(days=30)
        sub = new_subscription(user_id, plan_id)
        sub['status'] = 'active'
        sub['current_period_start'] = period_start
        sub['current_period_end'] = period_end
        db.subscriptions.replace_one({'user_id': user_id}, sub, upsert=True)

        invoice = new_invoice(user_id, str(db.subscriptions.find_one({'user_id': user_id})['_id']), order_doc['amount_paise'], period_start, period_end)
        db.invoices.insert_one(invoice)

        return Response({'status': 'success', 'plan_id': plan_id, 'period_end': period_end.isoformat()})
    except Exception as e:
        logger.error('[Billing] verify_payment error: %s', e)
        return Response({'error': 'Payment verification failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
def webhook(request):
    """
    Razorpay webhook handler.
    POST /api/billing/webhook/
    Register this URL in Razorpay dashboard.
    """
    try:
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
        if webhook_secret:
            sig = request.headers.get('X-Razorpay-Signature', '')
            expected = hmac.new(webhook_secret.encode(), request.body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, sig):
                return Response({'error': 'Invalid webhook signature'}, status=status.HTTP_400_BAD_REQUEST)

        payload = request.data
        event = payload.get('event')
        logger.info('[Billing] webhook event=%s', event)

        if event == 'subscription.charged':
            pass
        elif event == 'subscription.cancelled':
            pass
        elif event == 'payment.failed':
            pass

        return Response({'status': 'ok'})
    except Exception as e:
        logger.error('[Billing] webhook error: %s', e)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@supabase_required
def cancel_subscription(request):
    """
    Cancel the current user's subscription.
    POST /api/billing/cancel/
    """
    try:
        user_id = request.supabase_user.get('user_id')
        db = _db()
        result = db.subscriptions.update_one(
            {'user_id': user_id, 'status': 'active'},
            {'$set': {'status': 'cancelled', 'cancelled_at': datetime.utcnow(), 'updated_at': datetime.utcnow()}},
        )
        if result.modified_count == 0:
            return Response({'error': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'status': 'cancelled'})
    except Exception as e:
        logger.error('[Billing] cancel error: %s', e)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@supabase_required
def get_invoice(request, invoice_id):
    """
    GET /api/billing/invoice/<invoice_id>/
    """
    from bson import ObjectId
    try:
        user_id = request.supabase_user.get('user_id')
        db = _db()
        inv = db.invoices.find_one({'_id': ObjectId(invoice_id), 'user_id': user_id})
        if not inv:
            return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
        inv['_id'] = str(inv['_id'])
        if 'subscription_id' in inv:
            inv['subscription_id'] = str(inv['subscription_id'])
        return Response(inv)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
