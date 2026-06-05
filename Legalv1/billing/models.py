"""
Billing data models for MongoDB collections.

DORMANT — not wired into INSTALLED_APPS or urls.py.
Activate by:
  1. Add 'billing' to INSTALLED_APPS in settings.py
  2. Add path('api/billing/', include('billing.urls')) in Legalv1/urls.py
  3. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in legalenv
  4. pip install razorpay
"""

from datetime import datetime


SUBSCRIPTION_STATUSES = ('active', 'cancelled', 'expired', 'pending')
PAYMENT_STATUSES = ('created', 'authorized', 'captured', 'failed', 'refunded')
PLAN_IDS = ('trial', 'vakil_starter', 'vakil_pro', 'vakil_power', 'nagrik_free', 'nagrik_basic', 'nagrik_pro')


def new_subscription(user_id: str, plan_id: str, razorpay_subscription_id: str = None) -> dict:
    return {
        'user_id': user_id,
        'plan_id': plan_id,
        'status': 'pending',
        'razorpay_subscription_id': razorpay_subscription_id,
        'current_period_start': None,
        'current_period_end': None,
        'cancelled_at': None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
    }


def new_payment_order(user_id: str, plan_id: str, amount_paise: int, currency: str = 'INR') -> dict:
    return {
        'user_id': user_id,
        'plan_id': plan_id,
        'amount_paise': amount_paise,
        'currency': currency,
        'status': 'created',
        'razorpay_order_id': None,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
    }


def new_payment_transaction(
    user_id: str,
    order_id: str,
    razorpay_payment_id: str,
    razorpay_order_id: str,
    razorpay_signature: str,
    amount_paise: int,
) -> dict:
    return {
        'user_id': user_id,
        'order_id': order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_signature': razorpay_signature,
        'amount_paise': amount_paise,
        'status': 'captured',
        'created_at': datetime.utcnow(),
    }


def new_invoice(user_id: str, subscription_id: str, amount_paise: int, period_start, period_end) -> dict:
    return {
        'user_id': user_id,
        'subscription_id': subscription_id,
        'amount_paise': amount_paise,
        'currency': 'INR',
        'status': 'paid',
        'period_start': period_start,
        'period_end': period_end,
        'issued_at': datetime.utcnow(),
    }
