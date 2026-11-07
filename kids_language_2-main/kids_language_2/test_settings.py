"""Local test configuration; never use this module for deployment."""
import os
os.environ.setdefault('SECRET_KEY', 'test-only-key-for-offline-regression-checks')
from .settings import *  # noqa: F403

MQTT_ENABLED = False
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
             'legacy': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
