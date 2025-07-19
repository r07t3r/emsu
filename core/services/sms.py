import africastalking
from django.conf import settings

# Initialize once
africastalking.initialize(
    username=settings.AFRICASTALKING_USERNAME,
    api_key=settings.AFRICASTALKING_API_KEY
)
_sms = africastalking.SMS

def send_sms(to: str, message: str) -> dict:
    """
    Send an SMS via Africa’s Talking.
    `to` must include country code, e.g. "+2348012345678".
    """
    response = _sms.send(message, [to], sender_id=settings.AFRICASTALKING_SENDER)
    return response  # production: log or inspect this
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone_number, message):
    """
    Send SMS using a third-party service (e.g., Twilio, African SMS providers)
    This is a placeholder implementation - replace with actual SMS service
    """
    try:
        # Example implementation for African SMS providers
        # Replace with actual SMS service configuration
        
        if hasattr(settings, 'SMS_API_URL') and hasattr(settings, 'SMS_API_KEY'):
            payload = {
                'to': phone_number,
                'message': message,
                'api_key': settings.SMS_API_KEY
            }
            
            response = requests.post(
                settings.SMS_API_URL,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"SMS sent successfully to {phone_number}")
                return True
            else:
                logger.error(f"SMS failed to {phone_number}: {response.text}")
                return False
        else:
            # Development/testing mode - just log the message
            logger.info(f"SMS to {phone_number}: {message}")
            return True
            
    except Exception as e:
        logger.error(f"SMS service error: {str(e)}")
        return False


def send_bulk_sms(phone_numbers, message):
    """
    Send SMS to multiple recipients
    """
    results = []
    for phone_number in phone_numbers:
        result = send_sms(phone_number, message)
        results.append({
            'phone_number': phone_number,
            'success': result
        })
    
    return results
