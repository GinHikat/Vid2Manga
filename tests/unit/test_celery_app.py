import os
import sys
import unittest

# Ensure root directory and App/backend are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "App", "backend")
for d in [root_dir, backend_dir]:
    if d not in sys.path:
        sys.path.insert(0, d)

from modules.mlops.celery_app import celery_app, is_redis_available

class TestCeleryAppConfig(unittest.TestCase):

    def test_celery_app_initialization(self):
        """Verifies that Celery app instance is properly initialized or gracefully handled."""
        if celery_app is not None:
            self.assertEqual(celery_app.main, "vid2manga_worker")
        else:
            self.assertIsNone(celery_app)

    def test_redis_availability_check(self):
        """Verifies that is_redis_available returns a boolean without throwing exceptions."""
        res = is_redis_available()
        self.assertIsInstance(res, bool)

if __name__ == "__main__":
    unittest.main()
