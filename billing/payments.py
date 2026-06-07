import logging
from typing import Dict

logger = logging.getLogger(__name__)


def process_card_payment(card_token: str, amount: float, invoice_number: str) -> Dict:
    """
    Placeholder card payment integration.

    - If `stripe` is installed and `STRIPE_API_KEY` is set in env, this function
      will attempt a minimal Stripe charge (implementation intentionally basic).
    - Otherwise returns a standardized 'not implemented' dict so callers can
      handle the failure gracefully.
    """
    try:
        import stripe
        from decouple import config
    except Exception:
        logger.info('Stripe not installed or unavailable — card processing not implemented.')
        return {'status': 'error', 'error': 'card_processing_unavailable'}

    api_key = config('STRIPE_API_KEY', default='')
    if not api_key:
        logger.warning('STRIPE_API_KEY not set — skipping card charge.')
        return {'status': 'error', 'error': 'stripe_api_key_missing'}

    stripe.api_key = api_key
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(round(amount * 100)),
            currency='kes' if False else 'usd',
            payment_method=card_token,
            confirm=True,
            description=f'Payment for {invoice_number}',
        )
        return {'status': 'success', 'id': intent.id}
    except Exception as e:
        logger.exception('Stripe charge failed')
        return {'status': 'error', 'error': str(e)}
