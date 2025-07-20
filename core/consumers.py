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
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Message, MessageRecipient, Notification
from .utils.notifications import create_notification

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time messaging"""
    
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.user_group_name = f"user_{self.user.id}"
        
        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected for user: {self.user.email}")
    
    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        logger.info(f"WebSocket disconnected for user: {self.user.email}")
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'send_message':
                await self.handle_send_message(data)
            elif message_type == 'mark_read':
                await self.handle_mark_read(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'join_room':
                await self.handle_join_room(data)
            elif message_type == 'leave_room':
                await self.handle_leave_room(data)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON data'
            }))
        except Exception as e:
            logger.error(f"Error in WebSocket receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    async def handle_send_message(self, data):
        """Handle sending a new message"""
        try:
            recipient_ids = data.get('recipients', [])
            subject = data.get('subject', '')
            body = data.get('body', '')
            message_type = data.get('message_type', 'private')
            is_urgent = data.get('is_urgent', False)
            
            if not recipient_ids or not body:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Recipients and message body are required'
                }))
                return
            
            # Create message in database
            message = await self.create_message(
                sender=self.user,
                recipient_ids=recipient_ids,
                subject=subject,
                body=body,
                message_type=message_type,
                is_urgent=is_urgent
            )
            
            # Send to all recipients
            for recipient_id in recipient_ids:
                await self.channel_layer.group_send(
                    f"user_{recipient_id}",
                    {
                        'type': 'new_message',
                        'message': {
                            'id': str(message.id),
                            'sender': {
                                'id': str(self.user.id),
                                'name': self.user.get_full_name(),
                                'email': self.user.email
                            },
                            'subject': subject,
                            'body': body,
                            'is_urgent': is_urgent,
                            'created_at': message.created_at.isoformat(),
                            'message_type': message_type
                        }
                    }
                )
            
            # Send confirmation to sender
            await self.send(text_data=json.dumps({
                'type': 'message_sent',
                'message_id': str(message.id),
                'timestamp': message.created_at.isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to send message'
            }))
    
    async def handle_mark_read(self, data):
        """Mark a message as read"""
        try:
            message_id = data.get('message_id')
            if message_id:
                await self.mark_message_read(message_id, self.user.id)
                await self.send(text_data=json.dumps({
                    'type': 'message_read',
                    'message_id': message_id
                }))
        except Exception as e:
            logger.error(f"Error marking message as read: {str(e)}")
    
    async def handle_typing(self, data):
        """Handle typing indicators"""
        recipient_id = data.get('recipient_id')
        is_typing = data.get('is_typing', False)
        
        if recipient_id:
            await self.channel_layer.group_send(
                f"user_{recipient_id}",
                {
                    'type': 'typing_indicator',
                    'user': {
                        'id': str(self.user.id),
                        'name': self.user.get_full_name()
                    },
                    'is_typing': is_typing
                }
            )
    
    async def handle_join_room(self, data):
        """Join a chat room"""
        room_id = data.get('room_id')
        if room_id:
            self.room_group_name = f"room_{room_id}"
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
    
    async def handle_leave_room(self, data):
        """Leave a chat room"""
        room_id = data.get('room_id')
        if room_id and hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    # WebSocket message handlers
    async def new_message(self, event):
        """Send new message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message']
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'user': event['user'],
            'is_typing': event['is_typing']
        }))
    
    async def notification(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    @database_sync_to_async
    def create_message(self, sender, recipient_ids, subject, body, message_type, is_urgent):
        """Create a new message in the database"""
        message = Message.objects.create(
            sender=sender,
            subject=subject,
            body=body,
            message_type=message_type,
            is_urgent=is_urgent
        )
        
        # Create message recipients
        recipients = User.objects.filter(id__in=recipient_ids)
        for recipient in recipients:
            MessageRecipient.objects.create(
                message=message,
                recipient=recipient
            )
            
            # Create notification for urgent messages
            if is_urgent:
                create_notification(
                    recipient=recipient,
                    title=f"Urgent Message from {sender.get_full_name()}",
                    message=subject or body[:50] + "...",
                    notification_type="warning"
                )
        
        return message
    
    @database_sync_to_async
    def mark_message_read(self, message_id, user_id):
        """Mark a message as read"""
        try:
            recipient = MessageRecipient.objects.get(
                message_id=message_id,
                recipient_id=user_id
            )
            recipient.is_read = True
            recipient.read_at = timezone.now()
            recipient.save()
        except MessageRecipient.DoesNotExist:
            pass


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.notification_group_name = f"notifications_{self.user.id}"
        
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'mark_notification_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
        except Exception as e:
            logger.error(f"Error in notification WebSocket: {str(e)}")
    
    async def send_notification(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=self.user
            )
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
        except Notification.DoesNotExist:
            pass
