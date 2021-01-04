"""
WSGI config for IDEAS project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os, sys
sys.path.append('/home/carter/djangostack-2.2.17-0/apps/django/django_projects/IDEAS')
os.environ.setdefault("PYTHON_EGG_CACHE", "/home/carter/djangostack-2.2.17-0/apps/django/django_projects/IDEAS/egg_cache")


from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'IDEAS.settings')

application = get_wsgi_application()
