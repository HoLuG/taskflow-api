import pytest
from fastapi.testclient import TestClient

import app as taskflow


client = TestClient(taskflow.app)


@pytest.fixture(autouse=True)
def reset_tasks():
    taskflow.tasks.clear()
    taskflow.next_task_id = 1


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version():
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json()["name"] == taskflow.APP_NAME
    assert response.json()["version"] == taskflow.APP_VERSION


def test_create_and_get_task():
    response = client.post(
        "/tasks",
        json={
            "title": "Prepare course project",
            "description": "Implement TaskFlow",
            "priority": "high",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["id"] == 1
    assert created["status"] == "todo"

    fetched = client.get("/tasks/1")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Prepare course project"


def test_create_task_rejects_empty_title():
    response = client.post("/tasks", json={"title": ""})

    assert response.status_code == 422


def test_missing_task_returns_404():
    response = client.get("/tasks/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_update_task_status():
    created = client.post(
        "/tasks",
        json={"title": "Write tests"},
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"status": "done"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_filter_and_stats():
    client.post("/tasks", json={"title": "Task A", "priority": "high"})
    client.post("/tasks", json={"title": "Task B", "priority": "low"})

    filtered = client.get("/tasks", params={"priority": "high"})
    assert filtered.status_code == 200
    assert filtered.json()["count"] == 1

    stats = client.get("/stats")
    assert stats.json() == {
        "total": 2,
        "todo": 2,
        "in_progress": 0,
        "done": 0,
    }


def test_delete_task():
    client.post("/tasks", json={"title": "Temporary task"})

    response = client.delete("/tasks/1")
    assert response.status_code == 200

    missing = client.get("/tasks/1")
    assert missing.status_code == 404
