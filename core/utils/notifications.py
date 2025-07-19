from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from core.models import Notification  # Fixed: Changed from .models to core.models

channel_layer = get_channel_layer()

def push_notification(notification: Notification):
    """
    Send notification data to WebSocket group `notifications_<user_id>`.
    """
    group = f'notifications_{notification.user_id}'
    payload = {
        'id': str(notification.id),
        'is_read': notification.is_read,
        'content': str(notification.content_object),
        'timestamp': notification.created_at.isoformat(),
    }
    async_to_sync(channel_layer.group_send)(
        group,
        {
            'type': 'send_notification',
            'text': payload
        }
    )   