import requests, base64, logging
from datetime import datetime
from decouple import config

logger = logging.getLogger(__name__)

def get_mpesa_token():
    """Get M-Pesa OAuth token"""
    is_production = config('MPESA_ENVIRONMENT', default='sandbox') == 'production'
    base_url = 'https://api.safaricom.co.ke' if is_production else 'https://sandbox.safaricom.co.ke'
    url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"
    
    try:
        r = requests.get(url, auth=(config('MPESA_CONSUMER_KEY',''), config('MPESA_CONSUMER_SECRET','')), timeout=10)
        r.raise_for_status()
        return r.json().get('access_token','')
    except Exception as e:
        logger.error(f"Failed to get M-Pesa token: {e}")
        return None

def generate_password():
    """Generate M-Pesa password and timestamp"""
    shortcode = config('MPESA_SHORTCODE','174379')
    passkey   = config('MPESA_PASSKEY','')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw       = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(raw.encode()).decode(), timestamp

def validate_phone_number(phone_number):
    """Validate and format phone number to 254XXXXXXXXXX format"""
    phone = phone_number.strip()
    
    # Remove + if present
    if phone.startswith('+'): 
        phone = phone[1:]
    
    # Convert 0 to 254
    if phone.startswith('0'): 
        phone = '254' + phone[1:]
    
    # Add 254 if not present
    if not phone.startswith('254'):
        phone = '254' + phone
    
    # Validate format: 254 + 9 digit mobile number = 12 characters total
    if not phone.startswith('254') or len(phone) != 12:
        return None
    
    return phone


def is_valid_callback(callback_url: str) -> bool:
    """Ensure the callback URL is a public HTTPS URL (Daraja rejects localhost/http)."""
    if not callback_url:
        return False
    cb = callback_url.strip()
    # must be https and not localhost or 127.0.0.1
    if not cb.lower().startswith('https://'):
        return False
    if 'localhost' in cb or '127.0.0.1' in cb:
        return False
    return True

def stk_push(phone_number, amount, invoice_number):
    """Initiate M-Pesa STK push"""
    # Validate and format phone number
    phone = validate_phone_number(phone_number)
    if not phone:
        return {
            'ResponseCode': '1',
            'errorMessage': 'Invalid phone number format. Use format: 07XXXXXXXX or 254XXXXXXXXX'
        }
    
    # Validate callback URL before calling M-Pesa
    callback = config('MPESA_CALLBACK_URL','https://careos.com/billing/mpesa/callback/')
    if not is_valid_callback(callback):
        msg = (
            'Invalid MPESA_CALLBACK_URL. Daraja requires a public HTTPS callback URL. '
            'For local testing, expose your app with a tunnel (e.g. ngrok) and set '
            'MPESA_CALLBACK_URL to https://<your-subdomain>.ngrok.io/billing/mpesa/callback/'
        )
        logger.error(msg)
        return {'ResponseCode': '1', 'errorMessage': msg}

    # Get token
    token = get_mpesa_token()
    if not token:
        return {
            'ResponseCode': '1',
            'errorMessage': 'Failed to authenticate with M-Pesa. Check your credentials.'
        }
    
    password, timestamp = generate_password()
    shortcode = config('MPESA_SHORTCODE','174379')
    is_production = config('MPESA_ENVIRONMENT', default='sandbox') == 'production'
    
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {
        'BusinessShortCode': shortcode, 
        'Password': password, 
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline', 
        'Amount': int(amount),
        'PartyA': phone, 
        'PartyB': shortcode, 
        'PhoneNumber': phone,
        'CallBackURL': callback, 
        'AccountReference': invoice_number,
        'TransactionDesc': f'Payment for {invoice_number}',
    }
    
    try:
        base_url = 'https://api.safaricom.co.ke' if is_production else 'https://sandbox.safaricom.co.ke'
        url = f"{base_url}/mpesa/stkpush/v1/processrequest"
        
        logger.info(f"STK Push attempt - Phone: {phone}, Amount: {amount}, Invoice: {invoice_number}")
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        
        result = r.json()
        logger.info(f"STK Push response: {result}")
        return result
    except requests.exceptions.Timeout:
        error_msg = "M-Pesa request timed out. Please try again."
        logger.error(error_msg)
        return {'ResponseCode': '1', 'errorMessage': error_msg}
    except requests.exceptions.RequestException as e:
        error_msg = f"M-Pesa request failed: {str(e)}"
        logger.error(error_msg)
        if hasattr(e, 'response') and e.response is not None:
            try:
                return e.response.json()
            except Exception:
                return {'ResponseCode': '1', 'errorMessage': e.response.text or error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return {'ResponseCode': '1', 'errorMessage': error_msg}