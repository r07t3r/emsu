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
import logging
from django.db import transaction
from core.models import Notification

logger = logging.getLogger(__name__)


def create_notification(recipient, title, message, notification_type='info', **kwargs):
    """
    Create a notification for a user
    
    Args:
        recipient: User object
        title: Notification title
        message: Notification message
        notification_type: Type of notification (info, success, warning, error)
    """
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
                **kwargs
            )
            
            # TODO: Send real-time notification via WebSocket
            # This would trigger the WebSocket consumer to send notification
            
            logger.info(f"Notification created for {recipient.email}: {title}")
            return notification
            
    except Exception as e:
        logger.error(f"Failed to create notification: {str(e)}")
        return None


def create_bulk_notifications(recipients, title, message, notification_type='info'):
    """
    Create notifications for multiple users
    """
    notifications = []
    
    try:
        with transaction.atomic():
            for recipient in recipients:
                notification = Notification.objects.create(
                    recipient=recipient,
                    title=title,
                    message=message,
                    notification_type=notification_type
                )
                notifications.append(notification)
            
            logger.info(f"Bulk notifications created for {len(recipients)} users")
            return notifications
            
    except Exception as e:
        logger.error(f"Failed to create bulk notifications: {str(e)}")
        return []


def notify_parents_about_student(student, title, message, notification_type='info'):
    """
    Send notification to all parents of a student
    """
    try:
        parents = student.parentprofile_set.all()
        parent_users = [parent.user for parent in parents]
        
        return create_bulk_notifications(
            recipients=parent_users,
            title=title,
            message=message,
            notification_type=notification_type
        )
        
    except Exception as e:
        logger.error(f"Failed to notify parents about student {student.id}: {str(e)}")
        return []


def notify_teachers_about_student(student, title, message, notification_type='info'):
    """
    Send notification to all teachers of a student
    """
    try:
        # Get all teachers from student's enrolled classes
        enrollments = student.enrollment_set.filter(is_active=True)
        teacher_users = []
        
        for enrollment in enrollments:
            class_teachers = enrollment.class_enrolled.teacherprofile_set.all()
            teacher_users.extend([teacher.user for teacher in class_teachers])
        
        # Remove duplicates
        teacher_users = list(set(teacher_users))
        
        return create_bulk_notifications(
            recipients=teacher_users,
            title=title,
            message=message,
            notification_type=notification_type
        )
        
    except Exception as e:
        logger.error(f"Failed to notify teachers about student {student.id}: {str(e)}")
        return []
