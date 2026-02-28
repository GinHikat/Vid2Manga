import uuid
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    id: str
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# Simple in-memory storage
# In a production app, use Redis or a database
tasks: Dict[str, Task] = {}

def create_task() -> Task:
    task_id = str(uuid.uuid4())
    task = Task(id=task_id, status=TaskStatus.PENDING)
    tasks[task_id] = task
    return task

def get_task(task_id: str) -> Optional[Task]:
    return tasks.get(task_id)

def update_task_status(task_id: str, status: TaskStatus):
    if task_id in tasks:
        tasks[task_id].status = status

def update_task_result(task_id: str, result: Dict[str, Any]):
    if task_id in tasks:
        tasks[task_id].result = result
        tasks[task_id].status = TaskStatus.COMPLETED

def update_task_error(task_id: str, error: str):
    if task_id in tasks:
        tasks[task_id].error = error
        tasks[task_id].status = TaskStatus.FAILED
