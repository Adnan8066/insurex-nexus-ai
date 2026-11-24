try:
    # Load the Celery app when Celery is installed, so @shared_task binds to it.
    from .celery import app as celery_app
except ImportError:  # Celery not installed (for example a minimal local setup)
    celery_app = None

__all__ = ('celery_app',)
