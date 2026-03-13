from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Form
from schemas.video import VideoResponse, TaskResponse
from services.video_processor import process_video_task
from services.task_manager import create_task, get_task, TaskStatus
import shutil
import os
import uuid
from core.config import settings
from services.manga_processor import process_manga_generation

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

@router.post("/manga-layout")
async def create_manga_layout_endpoint(
    files: list[UploadFile] = File(...),
    width: int = Form(1000),
    height: int = Form(1400),
    num_frames: int = Form(8),
    seed: int = Form(42),
    stylize_style: str = Form("c"),
    segment_human: bool = Form(False),
    show_mask: bool = Form(False)
):
    """
    Generate a manga layout from uploaded images.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    # Save files to INPUT_DIR
    image_paths = []
    for file in files:
        # Generate a unique filename to avoid collisions
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_location = os.path.join(settings.INPUT_DIR, unique_filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        image_paths.append(file_location)
    
    try:
        manga_urls = await process_manga_generation(
            image_paths=image_paths,
            width=width,
            height=height,
            num_frames=num_frames,
            seed=seed,
            stylize_style=stylize_style,
            segment_human=segment_human,
            show_mask=show_mask
        )
        return {"manga_urls": manga_urls}
    except Exception as e:
        import traceback
        print(f"Error in manga-layout endpoint: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
