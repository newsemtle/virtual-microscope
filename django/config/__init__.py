__version__ = "[feature/internationalization] 2025.05.15 commit-1"


from .celery import app as celery_app

__all__ = ("celery_app",)
