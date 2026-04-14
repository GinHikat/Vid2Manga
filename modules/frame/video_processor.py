import os
import shutil
import traceback
from fastapi import UploadFile, HTTPException
from core.config import settings
from modules.speech.process_audio import split_video_audio, speech2text
from modules.task_manager import update_task_status, update_task_error, update_task_result, TaskStatus

async def process_video(file: UploadFile) -> tuple[str, str, str | None]:
    """Processes video: saves, splits audio/video, and transcribes."""
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")
    
    try:
        file_location = os.path.join(settings.INPUT_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        audio_path, video_path = split_video_audio(file_location)
        
        # Relative URLs for frontend
        audio_rel = os.path.relpath(audio_path, settings.OUTPUT_DIR).replace("\\", "/")
        video_rel = os.path.relpath(video_path, settings.OUTPUT_DIR).replace("\\", "/")
        
        res = speech2text(os.path.basename(audio_path))
        return f"/output/{video_rel}", f"/output/{audio_rel}", res.get("text", "")

    except Exception as e:
        print(f"Error in process_video: {e}\n{traceback.format_exc()}")
        if hasattr(e, 'stderr'): print(f"FFmpeg stderr: {e.stderr}")
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

async def process_video_task(task_id: str, file_location: str, original_filename: str, language: str = "en"):
    """Background task for video processing."""
    try:
        update_task_status(task_id, TaskStatus.PROCESSING)
        audio_path, video_path = split_video_audio(file_location)
        
        audio_rel = os.path.relpath(audio_path, settings.OUTPUT_DIR).replace("\\", "/")
        video_rel = os.path.relpath(video_path, settings.OUTPUT_DIR).replace("\\", "/")
        
        res = speech2text(os.path.basename(audio_path), language=language)
        
        update_task_result(task_id, {
            "video_url": f"/output/{video_rel}",
            "audio_url": f"/output/{audio_rel}",
            "text": res.get("text", ""),
            "segments": res.get("segments", [])
        })
    except Exception as e:
        stderr_msg = f" | FFmpeg stderr: {e.stderr}" if hasattr(e, 'stderr') else ""
        print(f"Error task {task_id}: {e}{stderr_msg}\n{traceback.format_exc()}")
        update_task_error(task_id, f"Processing failed: {str(e)}{stderr_msg}")
