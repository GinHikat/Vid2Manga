from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from schemas.video import VideoResponse, TaskResponse
from services.video_processor import process_video_task
from services.task_manager import create_task, get_task, TaskStatus
import shutil
import os
from core.config import settings

router = APIRouter()

@router.post("/convert", response_model=TaskResponse)
async def convert_video_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("en")
):
    """
    Upload a video file to separate audio and video components in the background.
    """
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a video.")

    task = create_task()
    
    # Save the file first
    file_location = os.path.join(settings.INPUT_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Add background task
    background_tasks.add_task(process_video_task, task.id, file_location, file.filename, language)
    
    return TaskResponse(task_id=task.id, status="pending")

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Check the status of a background task.
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task
