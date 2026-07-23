import os
import sys

# Ensure project root and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from core.config import settings

celery_app = None

try:
    from celery import Celery

    # Initialize Celery application instance
    celery_app = Celery(
        "vid2manga_worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=["modules.mlops.tasks"]
    )

    # Celery Configuration Settings
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=1800,  # 30 minute hard time limit per video processing task
        result_expires=86400,  # Cache task results in Redis for 24 hours
    )
except ImportError:
    pass

def is_redis_available() -> bool:
    """Helper function to check if Redis broker and Celery are available."""
    if celery_app is None:
        return False
    try:
        import redis
        client = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=1.0)
        return client.ping()
    except Exception:
        return False
