import fakeredis
import pytest
from fastapi.testclient import TestClient

import app.tasks as tasks
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    monkeypatch.setattr(tasks, "_client", fakeredis.FakeRedis(decode_responses=True))


def compute(index):
    response = client.post("/fibonacci", json={"index": index})
    assert response.status_code == 202
    task_id = response.json()["task_id"]
    return task_id


def test_fibonacci_normal_case():
    task_id = compute(10)
    pending = client.get(f"/fibonacci/tasks/{task_id}").json()
    assert pending["status"] == "pending"
    assert "value" not in pending

    assert tasks.work_once(timeout=1)
    output = client.get(f"/fibonacci/tasks/{task_id}").json()
    assert output["status"] == "done"
    assert output["index"] == 10
    assert output["value"] == "55"


def test_fibonacci_zero():
    task_id = compute(0)
    tasks.work_once(timeout=1)
    output = client.get(f"/fibonacci/tasks/{task_id}").json()
    assert output["status"] == "done"
    assert output["value"] == "0"


def test_unknown_task_returns_404():
    response = client.get("/fibonacci/tasks/does-not-exist")
    assert response.status_code == 404


def test_fibonacci_negative_index_returns_400():
    response = client.post("/fibonacci", json={"index": -1})
    assert response.status_code == 400
    assert response.json() == {"detail": "index must be >= 0"}


def test_index_page_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
