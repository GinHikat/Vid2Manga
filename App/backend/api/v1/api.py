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

router = APIRouter()

@router.post("/convert", response_model=TaskResponse)
async def convert_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Form("en")
):
    """Uploads video and starts background processing."""
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Invalid file type.")

    task = create_task()
    file_path = os.path.join(settings.INPUT_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    background_tasks.add_task(process_video_task, task.id, file_path, file.filename, language)
    return TaskResponse(task_id=task.id, status="pending")

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """Returns task status and result."""
    task = get_task(task_id)
    if not task: raise HTTPException(status_code=404, detail="Task not found")
    return task

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
