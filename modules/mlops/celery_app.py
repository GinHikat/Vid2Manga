import os
import sys

# Ensure project root and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from dotenv import load_dotenv
load_dotenv()

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
    celery_conf = {
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        "task_track_started": True,
        "task_time_limit": 1800,  # 30 minute hard time limit per video processing task
        "result_expires": 86400,  # Cache task results in Redis for 24 hours
    }

    # Automatically enable SSL for Upstash rediss:// URLs
    if settings.REDIS_URL.startswith("rediss://"):
        import ssl
        ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE}
        celery_conf["broker_use_ssl"] = ssl_opts
        celery_conf["redis_backend_use_ssl"] = ssl_opts

    celery_app.conf.update(**celery_conf)
except ImportError:
    pass

def is_redis_available() -> bool:
    """Helper function to check if Redis broker connection is reachable."""
    if celery_app is None or not settings.REDIS_URL:
        return False
    try:
        import redis
        url = settings.REDIS_URL
        if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
            url = url + ("&" if "?" in url else "?") + "ssl_cert_reqs=none"
        client = redis.Redis.from_url(url, socket_timeout=2.0)
        return client.ping()
    except Exception as e:
        return False

def is_celery_worker_active() -> bool:
    """Helper function to check if an active Celery worker process is online and listening."""
    if not is_redis_available():
        return False
    try:
        inspect = celery_app.control.inspect(timeout=0.5)
        workers = inspect.ping()
        return bool(workers and len(workers) > 0)
    except Exception:
        return False
