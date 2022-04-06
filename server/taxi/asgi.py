"""
ASGI config for taxi project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

import django
from channels.routing import get_default_application

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taxi.settings')

# application = get_asgi_application()


os.environ.setdefault('TAXI_DJANGO_SETTINGS_MODULE', 'taxi.settings')
django.setup()
application = get_default_application()
