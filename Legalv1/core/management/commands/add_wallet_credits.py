"""
Management command: add wallet credits to a user manually.

Usage:
  python manage.py add_wallet_credits --email user@example.com --credits 150 --note "UPI ref ABC123" --amount-inr 199
"""
import re

from django.core.management.base import BaseCommand, CommandError

from core.entitlements import _collection, _now, log_wallet_transaction


class Command(BaseCommand):
    help = 'Add wallet credits to a user (manual top-up, no payment gateway required).'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True, help='Target user email address.')
        parser.add_argument('--credits', required=True, type=int, help='Number of credits to add.')
        parser.add_argument('--note', default='', help='Free-text note (e.g. UPI ref, bank transfer ref).')
        parser.add_argument('--amount-inr', dest='amount_inr', type=float, default=None,
                            help='INR amount received (for accounting; optional).')

    def handle(self, *args, **options):
        email = options['email'].strip()
        credits = options['credits']
        note = options['note']
        amount_inr = options['amount_inr']

        if credits <= 0:
            raise CommandError('--credits must be a positive integer.')

        col = _collection()
        # Case-insensitive search so mixed-case emails stored by Supabase are found
        doc = col.find_one({'email': {'$regex': f'^{re.escape(email)}$', '$options': 'i'}})
        if not doc:
            raise CommandError(f'No entitlements document found for email: {email}')

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
            added_by='management_command',
        )

        updated = col.find_one({'_id': doc['_id']})
        new_balance = int(updated.get('wallet_credits_balance', 0))
        self.stdout.write(self.style.SUCCESS(
            f'Added {credits} credits to {email}. New balance: {new_balance} credits.'
        ))
        if amount_inr:
            self.stdout.write(f'  Amount received: ₹{amount_inr:.2f}  |  Note: {note}')
