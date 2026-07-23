import os
import uuid
import shutil
import traceback
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from core.config import settings
from schemas.video import TaskResponse
from modules.frame.video_processor import process_video_task
from modules.task_manager import create_task, get_task
from modules.frame.manga_processor import process_manga_generation

from modules.mlops.celery_app import is_redis_available, is_celery_worker_active, celery_app
from modules.mlops.tasks import process_video_celery_task
from celery.result import AsyncResult

router = APIRouter()

@router.post("/convert", response_model=TaskResponse)
async def convert_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("en")
):
    """Uploads video and starts background processing via Celery or BackgroundTasks fallback."""
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")

    file_path = os.path.join(settings.INPUT_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Upload to Google Drive if configured for cross-storage worker access
    from modules.mlops.gdrive_storage import is_gdrive_available, upload_file_to_drive
    
    target_video_param = file_path
    if is_gdrive_available():
        try:
            drive_res = upload_file_to_drive(file_path, drive_filename=file.filename, subfolder_name="input")
            target_video_param = f"gdrive:{drive_res['id']}"
        except Exception as e:
            print(f"Warning: Upload to Google Drive failed, using local path: {e}")

    # Try Celery task dispatch ONLY if an active worker is online AND Google Drive file ID is ready
    if is_celery_worker_active(timeout=1.5):
        if not target_video_param.startswith("gdrive:") and is_gdrive_available():
            try:
                drive_res = upload_file_to_drive(file_path, drive_filename=file.filename, subfolder_name="input")
                target_video_param = f"gdrive:{drive_res['id']}"
            except Exception as e:
                print(f"Warning: Failed uploading to Google Drive for Celery dispatch: {e}")

        if target_video_param.startswith("gdrive:"):
            try:
                async_result = process_video_celery_task.delay(
                    video_path=target_video_param,
                    filename=file.filename,
                    num_frames_per_page=7,
                    stylize_style="c",
                    language=language
                )
                return TaskResponse(task_id=async_result.id, status="pending")
            except Exception as e:
                print(f"Celery dispatch failed, falling back to BackgroundTasks: {e}")

    # Fallback to in-memory BackgroundTasks
    task = create_task()
    background_tasks.add_task(process_video_task, task.id, file_path, file.filename, language)
    return TaskResponse(task_id=task.id, status="pending")

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """Returns task status and result from task manager or Celery broker."""
    # Check in-memory task manager first
    task = get_task(task_id)
    if task:
        return task

    # Query Celery Result Backend if Redis is reachable
    if is_redis_available():
        try:
            res = AsyncResult(task_id, app=celery_app)
            if res.state == "PENDING":
                return {"id": task_id, "status": "pending", "progress": "Task queued in Redis"}
            elif res.state == "PROGRESS":
                info = res.info if isinstance(res.info, dict) else {}
                return {
                    "id": task_id, 
                    "status": "processing", 
                    "progress": info.get("progress_msg", "Processing video pipeline...")
                }
            elif res.state == "SUCCESS":
                result_data = res.result if isinstance(res.result, dict) else {}
                return {
                    "id": task_id,
                    "status": "completed",
                    "progress": "Pipeline finished successfully!",
                    "result": result_data
                }
            elif res.state == "FAILURE":
                return {"id": task_id, "status": "failed", "error": str(res.result)}
        except Exception as e:
            print(f"Error querying Celery status: {e}")

    raise HTTPException(status_code=404, detail="Task not found")

@router.post("/manga-layout")
async def create_manga_layout(
    files: list[UploadFile] = File(...),
    width: int = Form(1000),
    height: int = Form(1400),
    num_frames: int = Form(8),
    seed: int = Form(42),
    stylize_style: str = Form("c"),
    segment_human: bool = Form(False),
    show_mask: bool = Form(False)
):
    """Generates manga layout from uploaded images."""
    if not files: raise HTTPException(status_code=400, detail="No files.")

    image_paths = []
    for f in files:
        path = os.path.join(settings.INPUT_DIR, f"{uuid.uuid4()}_{f.filename}")
        with open(path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
        image_paths.append(path)
    
    try:
        urls = await process_manga_generation(
            image_paths, width, height, num_frames, seed, stylize_style, segment_human, show_mask
        )
        return {"manga_urls": urls}
    except Exception as e:
        print(f"Error in manga-layout: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
