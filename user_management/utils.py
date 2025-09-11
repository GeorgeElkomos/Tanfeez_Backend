from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import xx_notification

def send_notification(user, message, notification_type="info"):
    """
    Send a notification to a specific user
    
    Args:
        user: User object to send notification to
        message: The notification message
        notification_type: Type of notification (info, success, warning, error)
    """
    # Create database notification
    notification = xx_notification.objects.create(
        user=user,
        message=message
    )
    
    # Send real-time notification via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'user_{user.id}',
        {
            'type': 'send_notification',
            'message': {
                'id': notification.id,
                'message': message,
                'created_at': notification.created_at.isoformat(),
                'type': notification_type
            }
        }
    )
    
    return notification
