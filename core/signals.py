from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message, Announcement, Notification
from .utils.notifications import push_notification

@receiver(post_save, sender=Message)
def notify_on_message(sender, instance: Message, created, **kwargs):
    if created:
        # create Notification object
        notif = Notification.objects.create(
            user=instance.recipient,
            content_object=instance
        )
        push_notification(notif)

@receiver(post_save, sender=Announcement)
def notify_on_announcement(sender, instance: Announcement, created, **kwargs):
    if created:
        # notify all relevant users: if school is set, notify students+teachers in that school; else all users
        users = []
        if instance.school:
            users = list(instance.school.students.values_list('user_id', flat=True)) + \
                    list(instance.school.teachers.values_list('user_id', flat=True))
        else:
            from django.contrib.auth import get_user_model
            users = get_user_model().objects.values_list('id', flat=True)
        for uid in users:
            notif = Notification.objects.create(user_id=uid, content_object=instance)
            push_notification(notif)
