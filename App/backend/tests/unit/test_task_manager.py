
import pytest
from services.task_manager import create_task, get_task, update_task_status, update_task_result, update_task_error, tasks, TaskStatus, Task

def test_create_task():
    # Clear existing tasks
    tasks.clear()
    
    task = create_task()
    assert isinstance(task, Task)
    assert task.status == TaskStatus.PENDING
    assert task.id in tasks
    assert tasks[task.id] == task

def test_get_task():
    tasks.clear()
    task = create_task()
    retrieved_task = get_task(task.id)
    assert retrieved_task == task
    
    assert get_task("nonexistent") is None

def test_update_task_status():
    tasks.clear()
    task = create_task()
    
    update_task_status(task.id, TaskStatus.PROCESSING)
    assert tasks[task.id].status == TaskStatus.PROCESSING

def test_update_task_result():
    tasks.clear()
    task = create_task()
    
    result = {"foo": "bar"}
    update_task_result(task.id, result)
    
    assert tasks[task.id].status == TaskStatus.COMPLETED
    assert tasks[task.id].result == result

def test_update_task_error():
    tasks.clear()
    task = create_task()
    
    error_msg = "Something went wrong"
    update_task_error(task.id, error_msg)
    
    assert tasks[task.id].status == TaskStatus.FAILED
    assert tasks[task.id].error == error_msg
