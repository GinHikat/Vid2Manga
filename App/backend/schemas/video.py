from pydantic import BaseModel

class VideoResponse(BaseModel):
    video_url: str
    audio_url: str
    message: str = "Conversion successful"
    text: str | None = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str = "Task created"
