import logging
import os
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "TaskFlow")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEFAULT_TASK_PRIORITY = os.getenv("DEFAULT_TASK_PRIORITY", "medium")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

Priority = Literal["low", "medium", "high"]
Status = Literal["todo", "in_progress", "done"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    priority: Priority | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    priority: Priority | None = None
    status: Status | None = None


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="REST API for managing tasks",
)

# Учебная версия хранит данные в памяти.
tasks: dict[int, dict] = {}
next_task_id = 1


def get_task_or_404(task_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.on_event("startup")
def log_startup() -> None:
    logger.info("%s v%s started", APP_NAME, APP_VERSION)


@app.get("/")
def root() -> dict:
    return {"message": f"Welcome to {APP_NAME}"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict:
    return {"name": APP_NAME, "version": APP_VERSION}


@app.post("/tasks", status_code=201)
def create_task(task_data: TaskCreate) -> dict:
    global next_task_id

    priority = task_data.priority or DEFAULT_TASK_PRIORITY
    if priority not in ("low", "medium", "high"):
        raise HTTPException(
            status_code=500,
            detail="Invalid default task priority configuration",
        )

    task = {
        "id": next_task_id,
        "title": task_data.title,
        "description": task_data.description,
        "priority": priority,
        "status": "todo",
    }
    tasks[next_task_id] = task
    next_task_id += 1

    logger.info("Created task id=%s", task["id"])
    return task


@app.get("/tasks")
def list_tasks(
    status: Status | None = None,
    priority: Priority | None = None,
) -> dict:
    result = list(tasks.values())

    if status is not None:
        result = [task for task in result if task["status"] == status]

    if priority is not None:
        result = [task for task in result if task["priority"] == priority]

    return {"items": result, "count": len(result)}


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict:
    return get_task_or_404(task_id)


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, updates: TaskUpdate) -> dict:
    task = get_task_or_404(task_id)
    changes = updates.dict(exclude_unset=True)

    for field, value in changes.items():
        if value is not None:
            task[field] = value

    logger.info("Updated task id=%s", task_id)
    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int) -> dict:
    get_task_or_404(task_id)
    del tasks[task_id]

    logger.info("Deleted task id=%s", task_id)
    return {"message": "Task deleted", "id": task_id}


@app.get("/stats")
def task_stats() -> dict:
    return {
        "total": len(tasks),
        "todo": sum(t["status"] == "todo" for t in tasks.values()),
        "in_progress": sum(
            t["status"] == "in_progress" for t in tasks.values()
        ),
        "done": sum(t["status"] == "done" for t in tasks.values()),
    }
