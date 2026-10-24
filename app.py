import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import database

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
SortField = Literal["id", "title", "priority", "status", "due_date", "created_at"]
SortOrder = Literal["asc", "desc"]


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100, strip_whitespace=True)
    description: str = Field(default="", max_length=500)
    priority: Priority | None = None
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(
        default=None, min_length=1, max_length=100, strip_whitespace=True
    )
    description: str | None = Field(default=None, max_length=500)
    priority: Priority | None = None
    status: Status | None = None
    due_date: datetime | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    with database.get_connection():
        pass
    logger.info("%s v%s started", APP_NAME, APP_VERSION)
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="REST API for managing tasks",
    lifespan=lifespan,
)


def row_to_task(row) -> dict:
    return dict(row)


def get_task_or_404(task_id: int) -> dict:
    with database.get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return row_to_task(row)


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
    priority = task_data.priority or DEFAULT_TASK_PRIORITY

    if priority not in ("low", "medium", "high"):
        raise HTTPException(
            status_code=500,
            detail="Invalid default task priority configuration",
        )

    created_at = datetime.now(timezone.utc).isoformat()
    due_date = (
        task_data.due_date.isoformat()
        if task_data.due_date is not None
        else None
    )

    with database.get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks
                (title, description, priority, status, due_date, created_at)
            VALUES (?, ?, ?, 'todo', ?, ?)
            """,
            (
                task_data.title,
                task_data.description,
                priority,
                due_date,
                created_at,
            ),
        )
        task_id = cursor.lastrowid
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    task = row_to_task(row)
    logger.info("Created task id=%s", task["id"])
    return task


@app.get("/tasks")
def list_tasks(
    status: Status | None = None,
    priority: Priority | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: SortField = "created_at",
    order: SortOrder = "desc",
) -> dict:
    conditions = []
    parameters = []

    if status is not None:
        conditions.append("status = ?")
        parameters.append(status)

    if priority is not None:
        conditions.append("priority = ?")
        parameters.append(priority)

    where_clause = (
        f"WHERE {' AND '.join(conditions)}" if conditions else ""
    )

    sort_columns = {
        "id": "id",
        "title": "title",
        "priority": (
            "CASE priority WHEN 'high' THEN 1 "
            "WHEN 'medium' THEN 2 ELSE 3 END"
        ),
        "status": "status",
        "due_date": "due_date",
        "created_at": "created_at",
    }

    with database.get_connection() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM tasks {where_clause}",
            parameters,
        ).fetchone()[0]

        rows = connection.execute(
            f"""
            SELECT * FROM tasks
            {where_clause}
            ORDER BY {sort_columns[sort_by]} {order.upper()}, id ASC
            LIMIT ? OFFSET ?
            """,
            [*parameters, limit, offset],
        ).fetchall()

    return {
        "items": [row_to_task(row) for row in rows],
        "count": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict:
    return get_task_or_404(task_id)


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, updates: TaskUpdate) -> dict:
    get_task_or_404(task_id)

    changes = updates.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=422,
            detail="At least one field must be provided",
        )

    for field, value in changes.items():
        if value is None and field != "due_date":
            raise HTTPException(
                status_code=422,
                detail=f"Field '{field}' cannot be null",
            )

    if "due_date" in changes and changes["due_date"] is not None:
        changes["due_date"] = changes["due_date"].isoformat()

    allowed_columns = {
        "title",
        "description",
        "priority",
        "status",
        "due_date",
    }
    if not set(changes).issubset(allowed_columns):
        raise HTTPException(status_code=422, detail="Invalid update fields")

    assignments = ", ".join(f"{field} = ?" for field in changes)
    values = list(changes.values())

    with database.get_connection() as connection:
        connection.execute(
            f"UPDATE tasks SET {assignments} WHERE id = ?",
            [*values, task_id],
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    task = row_to_task(row)
    logger.info("Updated task id=%s", task_id)
    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int) -> dict:
    get_task_or_404(task_id)

    with database.get_connection() as connection:
        connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,),
        )

    logger.info("Deleted task id=%s", task_id)
    return {"message": "Task deleted", "id": task_id}


@app.get("/stats")
def task_stats() -> dict:
    with database.get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(status = 'todo'), 0) AS todo,
                COALESCE(SUM(status = 'in_progress'), 0) AS in_progress,
                COALESCE(SUM(status = 'done'), 0) AS done
            FROM tasks
            """
        ).fetchone()

    return dict(row)