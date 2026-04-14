import os
import subprocess
import ffmpeg
import whisper
from dotenv import load_dotenv

load_dotenv()

from core.config import settings

# Use settings from core.config
input_dir = settings.INPUT_DIR
audio_output_dir = os.path.join(settings.OUTPUT_DIR, 'audio')
video_output_dir = os.path.join(settings.OUTPUT_DIR, 'video')

for d in [audio_output_dir, video_output_dir]:
    os.makedirs(d, exist_ok=True)

def split_video_audio(input_file):
    """Splits video into mono 16k wav audio and soundless mp4 video."""
    if not os.path.isabs(input_file):
        potential_path = os.path.join(input_dir, input_file)
        if os.path.exists(potential_path):
            input_file = potential_path

    name = os.path.splitext(os.path.basename(input_file))[0]
    out_audio = os.path.join(audio_output_dir, f"{name}.wav")
    out_video = os.path.join(video_output_dir, f"{name}.mp4")

    # Audio extraction (PCM 16LE, 16kHz, Mono)
    ffmpeg.input(input_file).output(out_audio, acodec='pcm_s16le', ac=1, ar='16k').overwrite_output().run()
    # Video-only extraction
    ffmpeg.input(input_file).output(out_video, an=None).overwrite_output().run()

    return out_audio.replace('\\', '/'), out_video.replace('\\', '/')

def _transcribe_whisper(audio_path, language='en'):
    """Performs local transcription using OpenAI Whisper."""
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language=language, word_timestamps=True)
        
        segments = []
        for s in result["segments"]:
            segments.append({
                "speaker": "Unknown Speaker",
                "text": s["text"].strip(),
                "start": s["start"],
                "end": s["end"]
            })
        
        return {"text": result["text"].strip(), "segments": segments}
    except Exception as e:
        print(f"Whisper error: {e}")
        raise

def speech2text(audio_file, language='en'):
    """Transcribes audio using GCP STT with local Whisper fallback."""
    if not os.path.isabs(audio_file):
        audio_file = os.path.join(audio_output_dir, audio_file)

    if os.getenv("USE_WHISPER_ONLY", "false").lower() == "true":
        return _transcribe_whisper(audio_file, language)

    from .gcp_speech import transcribe_gcp
    
    mapping = {"en": "en-US", "vi": "vi-VN", "ja": "ja-JP", "zh": "zh-CN"}
    gcp_lang = mapping.get(language.lower(), f"{language.lower()}-{language.upper()}")

    try:
        return transcribe_gcp(audio_file, language_code=gcp_lang)
    except Exception as e:
        print(f"GCP failed, falling back: {e}")
        return _transcribe_whisper(audio_file, language)
