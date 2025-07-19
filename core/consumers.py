import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f'notifications_{self.user_id}'

        # Join group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receive message from group
    async def send_notification(self, event):
        # event['text'] is the notification payload
        await self.send_json(event['text'])
