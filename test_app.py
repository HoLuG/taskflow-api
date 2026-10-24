import pytest
from fastapi.testclient import TestClient
import app as taskflow


client = TestClient(taskflow.app)


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    db_file = tmp_path / "test_taskflow.db"
    monkeypatch.setattr(taskflow.database, "DB_PATH", str(db_file))

    with taskflow.database.get_connection():
        pass


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
    assert created["due_date"] is None

    fetched = client.get("/tasks/1")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Prepare course project"


def test_create_task_with_deadline():
    response = client.post(
        "/tasks",
        json={
            "title": "Finish project",
            "due_date": "2026-11-01T18:00:00+03:00",
        },
    )

    assert response.status_code == 201
    assert response.json()["due_date"] == "2026-11-01T18:00:00+03:00"


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


def test_update_can_clear_deadline():
    created = client.post(
        "/tasks",
        json={
            "title": "Task with deadline",
            "due_date": "2026-11-01T18:00:00+03:00",
        },
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"due_date": None},
    )

    assert response.status_code == 200
    assert response.json()["due_date"] is None


def test_update_rejects_empty_body():
    client.post("/tasks", json={"title": "Existing task"})

    response = client.patch("/tasks/1", json={})

    assert response.status_code == 422


def test_update_rejects_null_title():
    client.post("/tasks", json={"title": "Existing task"})

    response = client.patch("/tasks/1", json={"title": None})

    assert response.status_code == 422


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


def test_pagination():
    for title in ("Task A", "Task B", "Task C"):
        response = client.post("/tasks", json={"title": title})
        assert response.status_code == 201

    response = client.get(
        "/tasks",
        params={"limit": 2, "offset": 1, "sort_by": "id", "order": "asc"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["count"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert [task["title"] for task in data["items"]] == ["Task B", "Task C"]


def test_sort_by_priority():
    client.post("/tasks", json={"title": "Low priority", "priority": "low"})
    client.post("/tasks", json={"title": "High priority", "priority": "high"})
    client.post("/tasks", json={"title": "Medium priority", "priority": "medium"})

    response = client.get(
        "/tasks",
        params={"sort_by": "priority", "order": "asc"},
    )

    assert [task["priority"] for task in response.json()["items"]] == [
        "high",
        "medium",
        "low",
    ]


def test_pagination_rejects_invalid_limit():
    response = client.get("/tasks", params={"limit": 0})

    assert response.status_code == 422


def test_delete_task():
    client.post("/tasks", json={"title": "Temporary task"})

    response = client.delete("/tasks/1")
    assert response.status_code == 200

    missing = client.get("/tasks/1")
    assert missing.status_code == 404