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
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone_number, message, sender_name="EMSU"):
    """
    Send SMS using various SMS providers
    This is a placeholder implementation - integrate with your preferred SMS provider
    """
    try:
        # For production, integrate with providers like:
        # - Twilio
        # - Africa's Talking
        # - Bulk SMS Nigeria
        # - Infobip
        
        # Placeholder implementation
        if hasattr(settings, 'SMS_PROVIDER') and settings.SMS_PROVIDER == 'twilio':
            return send_sms_twilio(phone_number, message)
        elif hasattr(settings, 'SMS_PROVIDER') and settings.SMS_PROVIDER == 'africas_talking':
            return send_sms_africas_talking(phone_number, message, sender_name)
        else:
            # Mock implementation for development
            logger.info(f"SMS to {phone_number}: {message}")
            return True
            
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return False


def send_sms_twilio(phone_number, message):
    """
    Send SMS using Twilio
    """
    try:
        from twilio.rest import Client
        
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        
        message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Twilio SMS error: {str(e)}")
        return False


def send_sms_africas_talking(phone_number, message, sender_name):
    """
    Send SMS using Africa's Talking
    """
    try:
        import africastalking
        
        # Initialize Africa's Talking
        africastalking.initialize(
            settings.AFRICAS_TALKING_USERNAME,
            settings.AFRICAS_TALKING_API_KEY
        )
        
        sms = africastalking.SMS
        
        response = sms.send(
            message,
            [phone_number],
            sender_name
        )
        
        return response['SMSMessageData']['Recipients'][0]['status'] == 'Success'
        
    except Exception as e:
        logger.error(f"Africa's Talking SMS error: {str(e)}")
        return False


def send_bulk_sms(phone_numbers, message, sender_name="EMSU"):
    """
    Send SMS to multiple recipients
    """
    results = []
    for phone_number in phone_numbers:
        result = send_sms(phone_number, message, sender_name)
        results.append({
            'phone_number': phone_number,
            'success': result
        })
    
    return results


def format_phone_number(phone_number, country_code="+234"):
    """
    Format phone number for SMS sending
    """
    # Remove any non-digit characters
    clean_number = ''.join(filter(str.isdigit, phone_number))
    
    # Handle Nigerian numbers
    if clean_number.startswith('0'):
        clean_number = clean_number[1:]  # Remove leading 0
    
    if not clean_number.startswith('234'):
        clean_number = '234' + clean_number
    
    return '+' + clean_number


def send_otp_sms(phone_number, otp):
    """
    Send OTP via SMS
    """
    message = f"Your EMSU verification code is: {otp}. Valid for 10 minutes. Do not share this code."
    return send_sms(phone_number, message)


def send_notification_sms(phone_number, notification_type, message):
    """
    Send notification via SMS
    """
    prefix = {
        'urgent': '🚨 URGENT - ',
        'announcement': '📢 ',
        'reminder': '⏰ ',
        'grade': '📊 ',
        'attendance': '📅 '
    }.get(notification_type, '')
    
    full_message = f"{prefix}{message} - EMSU"
    return send_sms(phone_number, full_message)
