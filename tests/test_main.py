from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fibonacci_normal_case():
    response = client.get("/fibonacci/10")
    assert response.status_code == 200
    output = response.json() 
    assert output["index"] == 10
    assert output["value"] == 55


def test_fibonacci_zero():
    response = client.get("/fibonacci/0")
    assert response.status_code == 200
    output = response.json() 
    assert output["index"] == 0
    assert output["value"] == 0


def test_interface():
    response = client.get("/fibonacci/1")
    assert response.status_code == 200
    assert set({"index", "value"}).issubset(set(response.json().keys()))


def test_fibonacci_negative_index_returns_400():
    response = client.get("/fibonacci/-1")
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
