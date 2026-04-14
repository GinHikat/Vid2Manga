from pydantic import BaseModel

class SpeechSegment(BaseModel):
    speaker: str
    text: str
    start: float
    end: float

class VideoResponse(BaseModel):
    video_url: str
    audio_url: str
    message: str = "Conversion successful"
    text: str | None = None
    segments: list[SpeechSegment] | None = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str = "Task created"
