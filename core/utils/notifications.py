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
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def create_notification(recipient, title, message, notification_type="info", action_url="", metadata=None):
    """
    Create a notification and send it in real-time
    """
    try:
        from ..models import Notification
        
        notification = Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            action_url=action_url,
            metadata=metadata or {}
        )
        
        # Send real-time notification via WebSocket
        send_realtime_notification(recipient.id, notification)
        
        return notification
        
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}")
        return None


def send_realtime_notification(user_id, notification):
    """
    Send notification via WebSocket
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"notifications_{user_id}",
                {
                    "type": "send_notification",
                    "notification": {
                        "id": str(notification.id),
                        "title": notification.title,
                        "message": notification.message,
                        "notification_type": notification.notification_type,
                        "action_url": notification.action_url,
                        "created_at": notification.created_at.isoformat(),
                        "is_read": notification.is_read
                    }
                }
            )
    except Exception as e:
        logger.error(f"Error sending real-time notification: {str(e)}")


def notify_school_users(school, title, message, notification_type="info", exclude_user=None):
    """
    Send notification to all users in a school
    """
    try:
        from ..models import StudentProfile, TeacherProfile, PrincipalProfile
        
        # Get all users in the school
        users = set()
        
        # Add students
        for student in StudentProfile.objects.filter(school=school, is_active=True):
            users.add(student.user)
        
        # Add teachers
        for teacher in TeacherProfile.objects.filter(school=school, is_active=True):
            users.add(teacher.user)
        
        # Add principals
        for principal in PrincipalProfile.objects.filter(school=school, is_active=True):
            users.add(principal.user)
        
        # Remove excluded user
        if exclude_user:
            users.discard(exclude_user)
        
        # Send notifications
        for user in users:
            create_notification(
                recipient=user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            
    except Exception as e:
        logger.error(f"Error notifying school users: {str(e)}")


def notify_user_type(user_type, title, message, notification_type="info", school=None):
    """
    Send notification to all users of a specific type
    """
    try:
        users = User.objects.filter(user_type=user_type, is_active=True)
        
        if school:
            if user_type == 'student':
                users = users.filter(student_profile__school=school)
            elif user_type == 'teacher':
                users = users.filter(teacher_profile__school=school)
            elif user_type == 'principal':
                users = users.filter(principal_profile__school=school)
        
        for user in users:
            create_notification(
                recipient=user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            
    except Exception as e:
        logger.error(f"Error notifying user type: {str(e)}")


def notify_class_users(class_obj, title, message, notification_type="info"):
    """
    Send notification to all users in a class
    """
    try:
        from ..models import Enrollment
        
        # Get all students in the class
        enrollments = Enrollment.objects.filter(
            class_enrolled=class_obj,
            is_active=True
        ).select_related('student__user')
        
        for enrollment in enrollments:
            create_notification(
                recipient=enrollment.student.user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            
        # Notify class teacher
        if class_obj.class_teacher:
            create_notification(
                recipient=class_obj.class_teacher.user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            
        # Notify subject teachers
        from ..models import TeacherClass
        teacher_classes = TeacherClass.objects.filter(
            class_assigned=class_obj,
            is_active=True
        ).select_related('teacher__user')
        
        for tc in teacher_classes:
            create_notification(
                recipient=tc.teacher.user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            
    except Exception as e:
        logger.error(f"Error notifying class users: {str(e)}")


def notify_parents(student, title, message, notification_type="info"):
    """
    Send notification to a student's parents
    """
    try:
        for parent in student.parents.all():
            create_notification(
                recipient=parent.user,
                title=title,
                message=message,
                notification_type=notification_type
            )
            
    except Exception as e:
        logger.error(f"Error notifying parents: {str(e)}")


def bulk_notify(recipients, title, message, notification_type="info"):
    """
    Send notification to multiple recipients efficiently
    """
    try:
        from ..models import Notification
        
        notifications = []
        for recipient in recipients:
            notifications.append(
                Notification(
                    recipient=recipient,
                    title=title,
                    message=message,
                    notification_type=notification_type
                )
            )
        
        # Bulk create notifications
        created_notifications = Notification.objects.bulk_create(notifications)
        
        # Send real-time notifications
        for notification in created_notifications:
            send_realtime_notification(notification.recipient.id, notification)
            
    except Exception as e:
        logger.error(f"Error bulk notifying: {str(e)}")
