import shutil
import os
import sys
from fastapi import UploadFile, HTTPException
from core.config import settings
import traceback
import ffmpeg
from Speech.process_audio import split_video_audio, speech2text
from services.task_manager import update_task_status, update_task_error, update_task_result, TaskStatus

if settings.BASE_DIR not in sys.path:
    sys.path.append(settings.BASE_DIR)

async def process_video(file: UploadFile) -> tuple[str, str, str | None]:
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")
    
    try:
        file_location = os.path.join(settings.INPUT_DIR, file.filename)
        
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"Processing file: {file.filename}")
        
        audio_path, video_path = split_video_audio(file.filename)
        
        # Convert absolute paths to Relative URLs for serving on FE
        audio_rel_path = os.path.relpath(audio_path, settings.OUTPUT_DIR).replace("\\", "/")
        video_rel_path = os.path.relpath(video_path, settings.OUTPUT_DIR).replace("\\", "/")
        
        # speech-to-text
        audio_filename = os.path.basename(audio_path)
        print(f"Transcribing audio: {audio_filename}")
        transcription_result = speech2text(audio_filename)
        extracted_text = transcription_result.get("text", "")

        video_url = f"/output/{video_rel_path}"
        audio_url = f"/output/{audio_rel_path}"
        
        return video_url, audio_url, extracted_text

    except Exception as e:

        error_trace = traceback.format_exc()
        print(f"Error inside process_video service: {e}")
        print(f"Traceback: {error_trace}")
        
        # Capture FFmpeg stderr
        if hasattr(e, 'stderr'):
            try:
                stderr_output = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
                print(f"FFmpeg stderr: {stderr_output}")
            except Exception as decode_error:
                print(f"Could not decode stderr: {decode_error}")
        
        # Re-raise HTTP exceptions, wrap others
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)} | Check server logs for details.")

async def process_video_task(task_id: str, file_location: str, original_filename: str, language: str = "en"):
    try:
        update_task_status(task_id, TaskStatus.PROCESSING)
        print(f"Processing task {task_id}: {original_filename}")
        
        audio_path, video_path = split_video_audio(original_filename)
        
        # Convert absolute paths to Relative URLs for serving on FE
        audio_rel_path = os.path.relpath(audio_path, settings.OUTPUT_DIR).replace("\\", "/")
        video_rel_path = os.path.relpath(video_path, settings.OUTPUT_DIR).replace("\\", "/")
        
        # speech-to-text
        audio_filename = os.path.basename(audio_path)
        print(f"Transcribing audio: {audio_filename} in language {language}")
        transcription_result = speech2text(audio_filename, language=language)
        extracted_text = transcription_result.get("text", "")

        video_url = f"/output/{video_rel_path}"
        audio_url = f"/output/{audio_rel_path}"
        
        result = {
            "video_url": video_url,
            "audio_url": audio_url,
            "text": extracted_text
        }
        update_task_result(task_id, result)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error processing task {task_id}: {e}")
        print(f"Traceback: {error_trace}")
        
        # Capture FFmpeg stderr if available
        stderr_msg = ""
        if hasattr(e, 'stderr'):
            try:
                stderr_output = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
                stderr_msg = f" | FFmpeg stderr: {stderr_output}"
                print(stderr_msg)
            except Exception as decode_error:
                print(f"Could not decode stderr: {decode_error}")
        
        update_task_error(task_id, f"Processing failed: {str(e)}{stderr_msg}")
