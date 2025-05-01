import os

from celery import Celery
from dotenv import load_dotenv

from config.settings.base import DOTENV_PATH

load_dotenv(DOTENV_PATH)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
