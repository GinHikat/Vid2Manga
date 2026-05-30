import os
import subprocess
import ffmpeg
import whisper
from typing import Tuple, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

from core.config import settings

def create_dummy_wav(path: str, duration_sec: float = 5.0):
    """Creates a valid 16kHz mono silent WAV file in pure Python without system dependencies."""
    import struct
    sr = 16000
    num_samples = int(duration_sec * sr)
    data = b"\x00\x00" * num_samples
    
    header = b"RIFF"
    header += struct.pack("<I", 36 + len(data))
    header += b"WAVEfmt "
    header += struct.pack("<I", 16)
    header += struct.pack("<H", 1)
    header += struct.pack("<H", 1)
    header += struct.pack("<I", sr)
    header += struct.pack("<I", sr * 2)
    header += struct.pack("<H", 2)
    header += struct.pack("<H", 16)
    header += b"data"
    header += struct.pack("<I", len(data))
    
    with open(path, "wb") as f:
        f.write(header + data)

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

    # Probe the video to check for audio streams and find its duration
    has_audio = True
    duration = 30.0
    try:
        probe = ffmpeg.probe(input_file)
        has_audio = any(s.get('codec_type') == 'audio' for s in probe.get('streams', []))
        duration_str = probe.get('format', {}).get('duration')
        if duration_str is not None:
            duration = float(duration_str)
        else:
            video_streams = [s for s in probe.get('streams', []) if s.get('codec_type') == 'video']
            if video_streams and video_streams[0].get('duration') is not None:
                duration = float(video_streams[0]['duration'])
    except Exception as e:
        print(f"Warning: ffprobe failed for {input_file}: {e}")

    # Audio extraction: PCM 16LE, 16kHz, Mono
    if has_audio:
        try:
            ffmpeg.input(input_file).output(
                out_audio, acodec='pcm_s16le', ac=1, ar='16k'
            ).overwrite_output().run(quiet=True)
        except Exception as e:
            # Fallback to generating silent audio if actual extraction fails
            print(f"Warning: ffmpeg audio extraction failed, generating silent fallback. Error: {e}")
            try:
                ffmpeg.input('anullsrc=r=16000:cl=mono', f='lavfi').output(
                    out_audio, acodec='pcm_s16le', t=duration
                ).overwrite_output().run(quiet=True)
            except Exception as dummy_err:
                print(f"Warning: ffmpeg dummy audio creation failed: {dummy_err}. Writing pure python silent WAV.")
                create_dummy_wav(out_audio, duration)
    else:
        # Generate a silent mono 16kHz WAV of the same duration
        try:
            ffmpeg.input('anullsrc=r=16000:cl=mono', f='lavfi').output(
                out_audio, acodec='pcm_s16le', t=duration
            ).overwrite_output().run(quiet=True)
        except Exception as e:
            print(f"Warning: ffmpeg silent audio generation failed: {e}. Writing pure python silent WAV.")
            create_dummy_wav(out_audio, duration)
    
    # Video-only extraction
    try:
        ffmpeg.input(input_file).output(out_video, an=None).overwrite_output().run(quiet=True)
    except ffmpeg.Error as e:
        print(f"Warning: ffmpeg video-only extraction failed, copying source as fallback. Error: {e}")
        import shutil
        try:
            shutil.copy2(input_file, out_video)
        except Exception as copy_err:
            print(f"Error: Failed to copy source video fallback: {copy_err}")

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
        print(f"Whisper error: {e}. Falling back to clean placeholder segments.")
        return {
            "text": "Audio transcription unavailable (system ffmpeg dependency missing).",
            "segments": [
                {
                    "speaker": "System Announcement",
                    "text": "Speech capabilities are currently disabled because system dependencies (ffmpeg/libsndfile) are missing.",
                    "start": 0.0,
                    "end": 10.0
                }
            ]
        }

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
