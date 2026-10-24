import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("TASKFLOW_DB_PATH", "taskflow.db")


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 100),
                description TEXT NOT NULL DEFAULT ''
                    CHECK(length(description) <= 500),
                priority TEXT NOT NULL
                    CHECK(priority IN ('low', 'medium', 'high')),
                status TEXT NOT NULL DEFAULT 'todo'
                    CHECK(status IN ('todo', 'in_progress', 'done')),
                due_date TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()