import os
import io
import sys
from google.cloud import speech
from google.cloud import storage
from dotenv import load_dotenv

# Add project root to path to import local modules if needed
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

load_dotenv(os.path.join(project_root, '.env'))

def upload_to_gcs(local_file_path, bucket_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)
    return f"gs://{bucket_name}/{destination_blob_name}"

def delete_from_gcs(bucket_name, blob_name):
    """Deletes a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()

def transcribe_gcp(audio_file_path, language_code="en-US"):
    """
    Transcribes audio using GCP Speech-to-Text with word timestamps.
    Returns a dictionary compatible with Whisper's output format.
    """
    client = speech.SpeechClient()
    
    file_size = os.path.getsize(audio_file_path)
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    
    # Use GCS for any file to be safe with long_running_recognize
    # but only if bucket_name is provided. Otherwise try local (max 1min/10MB).
    use_gcs = False
    if bucket_name:
        use_gcs = True
        
    if use_gcs:
        blob_name = f"temp_stt_{os.path.basename(audio_file_path)}"
        print(f"Uploading {audio_file_path} to GCS bucket {bucket_name}...")
        gcs_uri = upload_to_gcs(audio_file_path, bucket_name, blob_name)
        audio = speech.RecognitionAudio(uri=gcs_uri)
    else:
        print(f"Reading local file {audio_file_path} (limit 60s/10MB for local files)...")
        with io.open(audio_file_path, "rb") as audio_file:
            content = audio_file.read()
        audio = speech.RecognitionAudio(content=content)

    # Note: encoding and sample_rate_hertz are optional if the file header specifies them (e.g. WAV)
    # But it's safer to specify if we know our ffmpeg output.
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        audio_channel_count=1,
        language_code=language_code,
        enable_word_time_offsets=True,
        enable_automatic_punctuation=True,
    )

    print("Starting transcription operation...")
    operation = client.long_running_recognize(config=config, audio=audio)
    
    print("Waiting for transcription to complete (this may take a few minutes)...")
    response = operation.result(timeout=900) # 15 min timeout

    # Convert GCP response to Whisper-like format
    full_text = ""
    segments = []
    
    for result in response.results:
        alternative = result.alternatives[0]
        full_text += alternative.transcript + " "
        
        # GCP doesn't always provide segments exactly like Whisper, 
        # but each 'result' in response.results is roughly a segment.
        segment = {
            "text": alternative.transcript,
            "start": alternative.words[0].start_time.total_seconds(),
            "end": alternative.words[-1].end_time.total_seconds(),
            "words": []
        }
        
        for word_info in alternative.words:
            segment["words"].append({
                "word": word_info.word,
                "start": word_info.start_time.total_seconds(),
                "end": word_info.end_time.total_seconds()
            })
        segments.append(segment)

    # Cleanup GCS if used
    if use_gcs:
        print(f"Cleaning up GCS blob {blob_name}...")
        try:
            delete_from_gcs(bucket_name, blob_name)
        except Exception as e:
            print(f"Warning: Failed to delete GCS blob: {e}")

    return {
        "text": full_text.strip(),
        "segments": segments
    }

if __name__ == "__main__":
    # Quick test if run directly
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_path", help="Path to audio file")
    args = parser.parse_args()
    
    if os.path.exists(args.audio_path):
        result = transcribe_gcp(args.audio_path)
        print("Transcription Result:")
        print(result["text"])
    else:
        print(f"File not found: {args.audio_path}")
