__version__ = "[feature/system-rework] 2025.05.01 commit-1"


from .celery import app as celery_app

__all__ = ("celery_app",)
