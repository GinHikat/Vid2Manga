
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Mock whisper before it gets imported by anything
sys.modules["whisper"] = MagicMock()

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, "..", ".."))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from main import app

@pytest.fixture(autouse=True)
def setup_test_env(tmp_path):
    # Override settings directories to use temporary path
    from core.config import settings
    
    original_input = settings.INPUT_DIR
    original_output = settings.OUTPUT_DIR
    
    settings.INPUT_DIR = str(tmp_path / "input")
    settings.OUTPUT_DIR = str(tmp_path / "output")
    
    os.makedirs(settings.INPUT_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    
    yield
    
    # Restore original settings
    settings.INPUT_DIR = original_input
    settings.OUTPUT_DIR = original_output

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_ffmpeg():
    with patch("ffmpeg.input") as mock:
        yield mock
