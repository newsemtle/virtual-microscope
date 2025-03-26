__version__ = "[feature/server-settings] 2025.03.27 commit-1"


from .celery import app as celery_app

__all__ = ("celery_app",)
