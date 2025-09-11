"""
ASGI config for budget_transfer project.
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from budget_transfer.urls import websocket_urlpatterns
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')

# application = get_asgi_application()

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})