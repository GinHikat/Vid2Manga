
import pytest
from unittest.mock import MagicMock, patch
from services.video_processor import process_video_task
from services.task_manager import TaskStatus, get_task, create_task, tasks
import os

@pytest.fixture
def mock_dependencies():
    with patch("services.video_processor.split_video_audio") as mock_split, \
         patch("services.video_processor.speech2text") as mock_speech:
        yield mock_split, mock_speech

@pytest.mark.asyncio
async def test_process_video_task_success(mock_dependencies):
    mock_split, mock_speech = mock_dependencies
    
    # Setup mocks
    mock_split.return_value = ("/output/audio.wav", "/output/video.mp4")
    mock_speech.return_value = {"text": "Hello world"}
    
    # Create a task
    task = create_task()
    
    # Run the task
    await process_video_task(task.id, "input/test.mp4", "test.mp4")
    
    # Verify task updated
    assert tasks[task.id].status == TaskStatus.COMPLETED
    result = tasks[task.id].result
    assert result["text"] == "Hello world"
    assert "video_url" in result
    assert "audio_url" in result
    
    # Verify mocks called
    mock_split.assert_called_once_with("test.mp4")
    mock_speech.assert_called_once()

@pytest.mark.asyncio
async def test_process_video_task_failure(mock_dependencies):
    mock_split, mock_speech = mock_dependencies
    
    # Setup mock allow failure
    mock_split.side_effect = Exception("Split failed")
    
    task = create_task()
    
    await process_video_task(task.id, "input/test.mp4", "test.mp4")
    
    assert tasks[task.id].status == TaskStatus.FAILED
    assert "Split failed" in tasks[task.id].error

