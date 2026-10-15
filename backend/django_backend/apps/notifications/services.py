from .models import Notification


def create_in_app_notification(recipient, notification_type, title, message, *, link='', related_object_type='', related_object_id='', priority='normal'):
    if not recipient:
        return None
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        priority=priority,
        title=title,
        message=message,
        link=link,
        related_object_type=related_object_type,
        related_object_id=str(related_object_id or ''),
    )
