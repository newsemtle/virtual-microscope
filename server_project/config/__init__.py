__version__ = "[feature/retouching] 2025.04.12 commit-1"


from .celery import app as celery_app

__all__ = ("celery_app",)
