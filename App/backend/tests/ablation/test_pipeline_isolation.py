import os
import pytest
from unittest.mock import MagicMock, patch
import sys

from modules.speech.process_audio import split_video_audio, speech2text

def test_split_video_audio(mock_ffmpeg):
    input_file = "test_video.mp4"
    
    # We mock ffmpeg.input().output().overwrite_output().run()
    # mock_ffmpeg is mocked 'ffmpeg.input'
    
    # Setup call chain
    mock_run = MagicMock()
    mock_overwrite = MagicMock(return_value=MagicMock(run=mock_run))
    mock_output = MagicMock(return_value=MagicMock(overwrite_output=mock_overwrite))
    mock_ffmpeg.return_value.output = mock_output
    
    audio_path, video_path = split_video_audio(input_file)
    
    assert audio_path.endswith('.wav')
    assert video_path.endswith('.mp4')
    # Use forward slashes as per function implementation
    assert '/' in audio_path
    assert '/' in video_path

    # Verify calls
    assert mock_ffmpeg.call_count == 2
    
@patch("modules.speech.process_audio._get_whisper_model")
@patch("modules.speech.diarization.diarizer.diarize")
def test_speech2text(mock_diarize, mock_get_model):
    # Setup diarize to return empty list (simulating no diarization)
    mock_diarize.return_value = []
    
    # Setup model.transcribe return value
    mock_model = MagicMock()
    mock_get_model.return_value = mock_model
    
    expected_transcription = {
        "text": "This is a test transcription",
        "segments": [{"text": "This is a test transcription", "start": 0.0, "end": 1.0}]
    }
    mock_model.transcribe.return_value = expected_transcription
    
    # We need to bypass GCP to test Whisper part
    with patch.dict(os.environ, {"USE_WHISPER_ONLY": "true"}):
        result = speech2text("test_audio.wav", language="en")
    
    assert result["text"] == expected_transcription["text"]
    assert len(result["segments"]) == 1
    assert result["segments"][0]["speaker"] == "Unknown Speaker"
    
    # Verify transcribe was called
    assert mock_model.transcribe.called
    call_args = mock_model.transcribe.call_args
    assert call_args.kwargs['language'] == 'en'
    assert call_args.kwargs['word_timestamps'] is True

