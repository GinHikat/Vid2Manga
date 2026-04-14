import os
import subprocess
import ffmpeg
import whisper
from typing import Tuple, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

from core.config import settings

# Global model cache to avoid reloading on every call
_WHISPER_MODEL = None

# Directory configuration from centralized settings
input_dir = settings.INPUT_DIR
audio_output_dir = os.path.join(settings.OUTPUT_DIR, 'audio')
video_output_dir = os.path.join(settings.OUTPUT_DIR, 'video')

for d in [audio_output_dir, video_output_dir]:
    os.makedirs(d, exist_ok=True)

def split_video_audio(input_file: str) -> Tuple[str, str]:
    """Splits a video file into a mono 16kHz WAV audio file and a soundless MP4 video file.

    Args:
        input_file: Path to the input video file (absolute or relative to input_dir).

    Returns:
        A tuple containing (audio_path, video_path) with forward slashes.
    """
    if not os.path.isabs(input_file):
        potential_path = os.path.join(input_dir, input_file)
        if os.path.exists(potential_path):
            input_file = potential_path

    name = os.path.splitext(os.path.basename(input_file))[0]
    out_audio = os.path.join(audio_output_dir, f"{name}.wav")
    out_video = os.path.join(video_output_dir, f"{name}.mp4")

    # Audio extraction: PCM 16LE, 16kHz, Mono
    ffmpeg.input(input_file).output(
        out_audio, acodec='pcm_s16le', ac=1, ar='16k'
    ).overwrite_output().run(quiet=True)
    
    # Video-only extraction
    ffmpeg.input(input_file).output(out_video, an=None).overwrite_output().run(quiet=True)

    return out_audio.replace('\\', '/'), out_video.replace('\\', '/')

def _get_whisper_model():
    """Lazy-loads and returns the Whisper 'base' model."""
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = whisper.load_model("base")
    return _WHISPER_MODEL

def _assign_speakers(transcription_segments: List[Dict[str, Any]], diarization_segments: List[Dict[str, Any]]):
    """Assigns speakers to Whisper segments based on overlap with diarization segments.

    Args:
        transcription_segments: List of segments from Whisper.
        diarization_segments: List of speaker segments from local diarizer.
    """
    for t_seg in transcription_segments:
        best_speaker = "Unknown Speaker"
        max_overlap = 0
        
        t_start, t_end = t_seg["start"], t_seg["end"]
        
        for d_seg in diarization_segments:
            d_start, d_end = d_seg["start"], d_seg["end"]
            
            # Calculate overlap
            overlap = min(t_end, d_end) - max(t_start, d_start)
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = d_seg["speaker"]
        
        t_seg["speaker"] = best_speaker

def _transcribe_whisper(audio_path: str, language: str = 'en') -> Dict[str, Any]:
    """Performs local transcription using the OpenAI Whisper model.

    Args:
        audio_path: Absolute path to the audio file.
        language: Language code for transcription (default is 'en').

    Returns:
        A dictionary containing the full 'text' and a list of 'segments' with speaker info.
    """
    try:
        # Load models
        model = _get_whisper_model()
        
        # Run transcription
        result = model.transcribe(audio_path, language=language, word_timestamps=True)
        
        segments = []
        for s in result["segments"]:
            segments.append({
                "speaker": "Unknown Speaker",
                "text": s["text"].strip(),
                "start": s["start"],
                "end": s["end"]
            })
        
        # Run local diarization if possible
        try:
            from .diarization import diarizer
            diarization_segments = diarizer.diarize(audio_path)
            if diarization_segments:
                _assign_speakers(segments, diarization_segments)
        except Exception as e:
            print(f"Local diarization failed or skipped: {e}")
        
        return {"text": result["text"].strip(), "segments": segments}
    except Exception as e:
        print(f"Whisper error: {e}")
        raise

def speech2text(audio_file: str, language: str = 'en') -> Dict[str, Any]:
    """Orchestrates speech-to-text transcription using GCP STT with local Whisper fallback.

    Args:
        audio_file: Name or path of the audio file to transcribe.
        language: ISO-639-1 language code (e.g., 'en', 'vi', 'ja').

    Returns:
        The transcription result dictionary (text and segments).
    """
    if not os.path.isabs(audio_file):
        audio_file = os.path.join(audio_output_dir, audio_file)

    if os.getenv("USE_WHISPER_ONLY", "false").lower() == "true":
        return _transcribe_whisper(audio_file, language)

    # Late import to avoid GCP dependencies if choosing Whisper only
    from .gcp_speech import transcribe_gcp
    
    mapping = {"en": "en-US", "vi": "vi-VN", "ja": "ja-JP", "zh": "zh-CN"}
    gcp_lang = mapping.get(language.lower(), f"{language.lower()}-{language.upper()}")

    try:
        return transcribe_gcp(audio_file, language_code=gcp_lang)
    except Exception as e:
        print(f"GCP failed, falling back to local Whisper: {e}")
        return _transcribe_whisper(audio_file, language)
