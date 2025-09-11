"""
WSGI config for budget_transfer project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_transfer.settings')

application = get_wsgi_application()
