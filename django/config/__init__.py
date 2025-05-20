__version__ = "[fix/bugs] 2025.05.20 commit-1"


from .celery import app as celery_app

__all__ = ("celery_app",)
