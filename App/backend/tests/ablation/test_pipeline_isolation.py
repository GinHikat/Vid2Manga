import os
import pytest
from unittest.mock import MagicMock, patch
import sys

import whisper
from Speech.process_audio import split_video_audio, speech2text, model

# The model is the mock because of sys.modules mocking
# Since model = whisper.load_model(...), model is the result of that call
# We need to configure the 'transcribe' method on this model mock
# However, `model` variable in process_audio.py holds the RETURN VALUE of `load_model`
# whisper.load_model is the mock function
# So model is the result of that mock function call.

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
    # split_video_audio calls ffmpeg.input twice
    assert mock_ffmpeg.call_count == 2
    
def test_speech2text():
    # Setup model.transcribe return value
    # model is the mock object from Speech.process_audio
    # The 'transcribe' method on it should return a result dict
    
    expected_result = {"text": "This is a test transcription"}
    model.transcribe.return_value = expected_result
    
    result = speech2text("test_audio.wav", language="en")
    
    assert result == expected_result
    # Verify transcribe was called with correct args
    # The first arg is absolute path constructed inside
    assert model.transcribe.called
    call_args = model.transcribe.call_args
    assert call_args.kwargs['language'] == 'en'
    assert call_args.kwargs['word_timestamps'] is True

