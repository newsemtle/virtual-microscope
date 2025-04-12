__version__ = "[hotfix] 2025.04.08 commit-1"


from .celery import app as celery_app

__all__ = ("celery_app",)
