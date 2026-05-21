"""
WSGI config for WorkSphere.

Exposes the WSGI callable as a module-level variable named ``application``.
For production deployment (Gunicorn, uWSGI, etc.)
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'worksphere.settings')

application = get_wsgi_application()
