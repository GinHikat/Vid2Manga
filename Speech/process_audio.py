import ffmpeg
import os
import sys
# import whisper # Kept for reference or fallback

# Optional: Fallback model if GCP fails or isn't configured
# model = whisper.load_model("base", device = 'cpu')

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

output_dir = os.path.join(project_root, 'output')
input_dir = os.path.join(project_root, 'input')

audio_dir = os.path.join(output_dir, 'audio')
video_dir = os.path.join(output_dir, 'video')

os.makedirs(audio_dir, exist_ok=True)
os.makedirs(video_dir, exist_ok=True)
os.makedirs(input_dir, exist_ok=True)

def split_video_audio(input_file_path):
    '''
    Separate a video into audio and raw video file

    Input:
        input_file_path: path to the original video file

    Output:
        file_name.wav: the extracted audio
        file_name.mp4: the extracted video without sound
    '''

    file_name = os.path.splitext(os.path.basename(input_file_path))[0]

    input_file_path = os.path.join(input_dir, input_file_path)

    output_audio = os.path.join(audio_dir, f'{file_name}.wav')
    output_video = os.path.join(video_dir, f'{file_name}.mp4')

    # Extract 16kHz Mono WAV for GCP Speech-to-Text
    ffmpeg.input(input_file_path).output(output_audio, ar=16000, ac=1).overwrite_output().run(capture_stdout=True, capture_stderr=True)

    ffmpeg.input(input_file_path).output(output_video, an=None).overwrite_output().run()

    return output_audio.replace('\\', '/'), output_video.replace('\\', '/')

def speech2text(input_audio_path, language = 'en'):
    '''
    Extract the sound in the audio to text with annotated timestamp

    Input:
        input_audio_path: path to the audio file

    Output:
        result: resulted text from speech
    '''

    input_audio_path = os.path.join(audio_dir, input_audio_path)

    # Use GCP for STT
    from Speech.gcp_speech import transcribe_gcp
    
    # Map simple language codes to GCP format if necessary
    gcp_lang = language
    if len(language) == 2:
        # Simple mapping for common ones
        mapping = {"en": "en-US", "vi": "vi-VN", "ja": "ja-JP", "zh": "zh-CN"}
        gcp_lang = mapping.get(language.lower(), f"{language.lower()}-{language.upper()}")

    try:
        result = transcribe_gcp(input_audio_path, language_code=gcp_lang)
    except Exception as e:
        print(f"GCP Transcription failed: {e}")
        print("Falling back to Whisper if available...")
        # Fallback to Whisper if you uncomment the model load above
        # result = model.transcribe(input_audio_path, language=language, word_timestamps=True)
        raise e

    return result

def diarization():
    pass