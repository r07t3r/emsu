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
