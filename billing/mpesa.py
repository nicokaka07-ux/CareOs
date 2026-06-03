import base64
import logging
import requests

from datetime import datetime
from decouple import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _base_url() -> str:
    env = str(config('MPESA_ENVIRONMENT', default='sandbox', cast=str)).strip().lower()
    return (
        'https://api.safaricom.co.ke'
        if env == 'production'
        else 'https://sandbox.safaricom.co.ke'
    )


def get_mpesa_token() -> str | None:
    """
    Fetch a short-lived OAuth 2.0 bearer token from Daraja.

    Returns the access_token string on success, or None on failure.
    Each token is valid for ~1 hour; for a demo / low-traffic app
    fetching a fresh token per request is fine.  If you need caching,
    store the token + expiry in Django's cache backend.
    """
    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    consumer_key    = config('MPESA_CONSUMER_KEY', default='', cast=str)
    consumer_secret = config('MPESA_CONSUMER_SECRET', default='', cast=str)
    if not isinstance(consumer_key, str) or not isinstance(consumer_secret, str):
        logger.error("MPESA_CONSUMER_KEY or MPESA_CONSUMER_SECRET is not set in .env")
        return None

    consumer_key = consumer_key.strip()
    consumer_secret = consumer_secret.strip()

    if not consumer_key or not consumer_secret:
        logger.error("MPESA_CONSUMER_KEY or MPESA_CONSUMER_SECRET is not set in .env")
        return None

    auth = (consumer_key, consumer_secret)
    try:
        response = requests.get(
            url,
            auth=auth,
            timeout=15,
        )
        response.raise_for_status()
        token = response.json().get('access_token', '')
        if not token:
            logger.error("Daraja returned no access_token. Full response: %s", response.text)
            return None
        logger.debug("M-Pesa OAuth token acquired successfully.")
        return token

    except requests.exceptions.HTTPError as e:
        logger.error(
            "HTTP %s when fetching M-Pesa token: %s",
            e.response.status_code if e.response is not None else '?',
            e.response.text if e.response is not None else str(e),
        )
    except requests.exceptions.Timeout:
        logger.error("Timeout fetching M-Pesa OAuth token (>15 s).")
    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching M-Pesa token: %s", e)
    except Exception as e:
        logger.error("Unexpected error fetching M-Pesa token: %s", e)

    return None


def _generate_password() -> tuple[str, str]:
    """
    Generate the Daraja STK-push password and the matching timestamp.

    password  = base64( shortcode + passkey + timestamp )
    timestamp = YYYYMMDDHHmmss  (local server time)

    Returns (password, timestamp).
    """
    shortcode = config('MPESA_SHORTCODE', default='174379', cast=str)
    passkey   = config('MPESA_PASSKEY',   default='', cast=str)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw       = f"{shortcode}{passkey}{timestamp}"
    password  = base64.b64encode(raw.encode()).decode()
    return password, timestamp


def validate_phone_number(phone_number: str) -> str | None:
    """
    Normalise any common Kenyan phone format to 254XXXXXXXXX (12 digits).

    Accepted inputs:  07XXXXXXXX  |  7XXXXXXXX  |  2547XXXXXXXX  |  +2547XXXXXXXX
    Returns the normalised string, or None if the number is invalid.
    """
    phone = phone_number.strip()

    # Strip leading +
    if phone.startswith('+'):
        phone = phone[1:]

    # 0XXXXXXXXX  →  254XXXXXXXXX
    if phone.startswith('0'):
        phone = '254' + phone[1:]

    # 7XXXXXXXXX (9 digits, no country code)
    if not phone.startswith('254'):
        phone = '254' + phone

    # Final validation: must be exactly 12 digits and start with 2547
    if len(phone) != 12 or not phone.startswith('2547'):
        logger.warning("Phone number failed validation: %s", phone_number)
        return None

    return phone


def is_valid_callback(callback_url: str) -> bool:
    """
    Daraja requires a publicly reachable HTTPS URL.
    Reject localhost, 127.0.0.1, and plain HTTP.
    """
    if not callback_url:
        return False
    cb = callback_url.strip().lower()
    if not cb.startswith('https://'):
        return False
    if 'localhost' in cb or '127.0.0.1' in cb:
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Main entry-point
# ─────────────────────────────────────────────────────────────────────────────

def stk_push(phone_number: str, amount: float, invoice_number: str) -> dict:
    """
    Initiate a Lipa Na M-Pesa Online (STK Push) request.

    Parameters
    ----------
    phone_number    : Patient's phone in any supported format (see validate_phone_number).
    amount          : Amount to charge in KES (will be rounded to nearest integer).
    invoice_number  : Used as the AccountReference visible to the payer.

    Returns
    -------
    dict  – On success the dict contains at minimum:
                ResponseCode        '0'
                CheckoutRequestID   '<uuid>'
                MerchantRequestID   '<uuid>'
                CustomerMessage     'Success. ...'
            On failure it always contains:
                ResponseCode        non-'0' string
                errorMessage        human-readable reason
    """

    # ── 1. Validate phone ────────────────────────────────────────────────────
    phone = validate_phone_number(phone_number)
    if not phone:
        return {
            'ResponseCode': '1',
            'errorMessage': (
                f"Invalid phone number '{phone_number}'. "
                "Use format 07XXXXXXXX, 7XXXXXXXX, or 2547XXXXXXXX."
            ),
        }

    # ── 2. Validate callback URL ─────────────────────────────────────────────
    callback = config(
        'MPESA_CALLBACK_URL',
        default='https://example.com/billing/mpesa/callback/',
        cast=str,
    )
    if not isinstance(callback, str):
        callback = str(callback)
    if not is_valid_callback(callback):
        msg = (
            "MPESA_CALLBACK_URL is not a valid public HTTPS URL. "
            "Daraja requires a publicly reachable HTTPS endpoint. "
            "For local testing run ngrok and set MPESA_CALLBACK_URL to "
            "https://<subdomain>.ngrok-free.app/billing/mpesa/callback/"
        )
        logger.error(msg)
        return {'ResponseCode': '1', 'errorMessage': msg}

    # ── 3. Acquire OAuth token ───────────────────────────────────────────────
    token = get_mpesa_token()
    if not token:
        return {
            'ResponseCode': '1',
            'errorMessage': (
                "Could not authenticate with M-Pesa. "
                "Check MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET in .env, "
                "and ensure your Daraja app has the Lipa Na M-Pesa API subscribed."
            ),
        }

    # ── 4. Build payload ─────────────────────────────────────────────────────
    shortcode        = config('MPESA_SHORTCODE', default='174379', cast=str)
    password, timestamp = _generate_password()
    int_amount       = max(1, int(round(amount)))   # Daraja minimum is KES 1

    payload = {
        'BusinessShortCode': shortcode,
        'Password':          password,
        'Timestamp':         timestamp,
        'TransactionType':   'CustomerPayBillOnline',
        'Amount':            int_amount,
        'PartyA':            phone,
        'PartyB':            shortcode,
        'PhoneNumber':       phone,
        'CallBackURL':       callback,
        'AccountReference':  invoice_number[:12],   # Daraja limit: 12 chars
        'TransactionDesc':   f"Payment {invoice_number}"[:13],  # Daraja limit: 13 chars
    }

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type':  'application/json',
    }

    # ── 5. Call Daraja ───────────────────────────────────────────────────────
    url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"
    logger.info(
        "STK Push → phone=%s  amount=%s  invoice=%s  callback=%s",
        phone, int_amount, invoice_number, callback,
    )

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)

        # Log raw Daraja response regardless of status code
        logger.info("Daraja HTTP %s: %s", response.status_code, response.text)

        # Daraja returns 200 even for business-logic errors (wrong passkey, etc.)
        # so we parse the body rather than relying on raise_for_status alone.
        try:
            result = response.json()
        except ValueError:
            return {
                'ResponseCode': '1',
                'errorMessage': f"Non-JSON response from Daraja (HTTP {response.status_code}): {response.text[:300]}",
            }

        # HTTP-level error (e.g. 400 Bad Request from Daraja)
        if not response.ok:
            error_msg = (
                result.get('errorMessage')
                or result.get('ResultDesc')
                or result.get('error_description')
                or response.text[:300]
            )
            logger.error("Daraja error (HTTP %s): %s", response.status_code, error_msg)
            result.setdefault('ResponseCode', str(response.status_code))
            result.setdefault('errorMessage', error_msg)
            return result

        return result

    except requests.exceptions.Timeout:
        msg = "M-Pesa STK push request timed out (>15 s). Please try again."
        logger.error(msg)
        return {'ResponseCode': '1', 'errorMessage': msg}

    except requests.exceptions.ConnectionError as e:
        msg = f"Could not reach Safaricom servers: {e}"
        logger.error(msg)
        return {'ResponseCode': '1', 'errorMessage': msg}

    except requests.exceptions.RequestException as e:
        # Capture the Daraja response body when available
        if hasattr(e, 'response') and e.response is not None:
            try:
                return e.response.json()
            except Exception:
                return {'ResponseCode': '1', 'errorMessage': e.response.text or str(e)}
        msg = f"Unexpected request error: {e}"
        logger.error(msg)
        return {'ResponseCode': '1', 'errorMessage': msg}

    except Exception as e:
        msg = f"Unexpected error during STK push: {e}"
        logger.error(msg, exc_info=True)
        return {'ResponseCode': '1', 'errorMessage': msg}