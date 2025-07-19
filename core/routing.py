from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Client connects to receive notifications for their user ID
    re_path(r'ws/notifications/(?P<user_id>[0-9a-f-]+)/$', consumers.NotificationConsumer.as_asgi()),
]
