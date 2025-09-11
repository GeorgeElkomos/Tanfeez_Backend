from channels.generic.websocket import WebsocketConsumer
import json
from asgiref.sync import async_to_sync

class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            self.close()
        else:
            self.group_name = f'user_{user.id}'
            self.accept()
            async_to_sync(self.channel_layer.group_add)(
                self.group_name,
                self.channel_name
            )

    def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            async_to_sync(self.channel_layer.group_discard)(
                self.group_name,
                self.channel_name
            )

    def send_notification(self, event):
        message = event['message']
        self.send(text_data=json.dumps(message))