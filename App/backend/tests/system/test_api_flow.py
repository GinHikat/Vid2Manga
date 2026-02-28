
import pytest
from unittest.mock import patch, MagicMock
import os
import io

def test_convert_video_endpoint(client):
    # Mock the internal service calls to avoid real processing
    with patch("services.video_processor.split_video_audio") as mock_split, \
         patch("services.video_processor.speech2text") as mock_speech:
         
        # Setup mocks
        mock_split.return_value = ("output/audio.wav", "output/video.mp4")
        mock_speech.return_value = {"text": "System test transcription"}
        
        # Create a dummy video file in memory
        file_content = b"fake video content"
        file_name = "test_system.mp4"
        files = {"file": (file_name, file_content, "video/mp4")}
        
        # Send POST request
        response = client.post("/convert", files=files, data={"language": "en"})
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        
        task_id = data["task_id"]
        
        # Check output/input directory handling
        # Verify file was saved?
        # Since BackgroundTasks run after response, we might need to wait or rely on TestClient behavior
        # TestClient runs background tasks synchronously after the request.
        
        # Verify status endpoint
        status_response = client.get(f"/status/{task_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        # Since TestClient runs background tasks immediately, the task should be COMPLETED
        assert status_data["id"] == task_id
        assert status_data["status"] == "completed"
        assert status_data["result"]["text"] == "System test transcription"
