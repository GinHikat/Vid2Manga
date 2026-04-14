import io
import os
from google.cloud import speech
from dotenv import load_dotenv

load_dotenv()

def resolve_credentials_path():
    """Resolves absolute path for GOOGLE_APPLICATION_CREDENTIALS."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or os.path.isabs(creds_path):
        return creds_path
        
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    absolute_creds_path = os.path.join(project_root, creds_path)
    
    return absolute_creds_path if os.path.exists(absolute_creds_path) else os.path.join(os.getcwd(), creds_path)

# Initialize credentials
abs_creds = resolve_credentials_path()
if abs_creds:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_creds

def transcribe_gcp(audio_path, language_code="en-US"):
    """Transcribes audio using GCP Speech-to-Text (synchronous)."""
    client = speech.SpeechClient()
    
    with io.open(audio_path, "rb") as f:
        content = f.read()

    audio = speech.RecognitionAudio(content=content)
    diarization_config = speech.SpeakerDiarizationConfig(
        enable_speaker_diarization=True,
        min_speaker_count=1,
        max_speaker_count=10,
    )

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code=language_code,
        enable_word_time_offsets=True,
        diarization_config=diarization_config,
    )

    try:
        response = client.recognize(config=config, audio=audio)
    except Exception as e:
        if "payload size exceeds the limit" in str(e).lower():
            print("File too large for direct GCP upload.")
        raise e

    full_text = ""
    segments = []
    
    # Process results with diarization
    # GCP returns diarization tags in the last result's last alternative's words
    if response.results:
        last_result = response.results[-1]
        if last_result.alternatives:
            words_info = last_result.alternatives[0].words
            
            current_speaker = None
            current_segment = {"speaker": "", "text": "", "start": 0.0, "end": 0.0}
            
            for word_info in words_info:
                speaker_tag = f"Speaker {word_info.speaker_tag}"
                word = word_info.word
                start_time = word_info.start_time.total_seconds()
                end_time = word_info.end_time.total_seconds()

                if speaker_tag != current_speaker:
                    if current_speaker is not None:
                        segments.append(current_segment)
                    current_speaker = speaker_tag
                    current_segment = {
                        "speaker": speaker_tag,
                        "text": word,
                        "start": start_time,
                        "end": end_time
                    }
                else:
                    current_segment["text"] += " " + word
                    current_segment["end"] = end_time
            
            if current_segment["text"]:
                segments.append(current_segment)

        # Build full text from all alternatives
        for result in response.results:
            full_text += result.alternatives[0].transcript + " "

    return {"text": full_text.strip(), "segments": segments}
