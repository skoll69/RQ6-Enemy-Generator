import os
from django.core.wsgi import get_wsgi_application

# Ensure the settings module is correctly set. The project keeps settings.py at the repo root.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ.get('DJANGO_SETTINGS_MODULE', 'settings'))

application = get_wsgi_application()
