import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.db import DATABASE_URL, init_db
from app.main import app


@pytest.fixture
def client():
    try:
        psycopg.connect(DATABASE_URL, connect_timeout=2).close()
    except psycopg.OperationalError:
        pytest.skip("база данных недоступна")
    init_db()
    return TestClient(app)


@pytest.fixture
def credentials():
    # уникальный логин, чтобы тесты не мешали друг другу и повторным запускам
    return {"username": "user_" + uuid.uuid4().hex[:8], "password": "secret123"}


def test_register_login_me_logout(client, credentials):
    assert client.post("/register", json=credentials).status_code == 201

    assert client.post("/login", json=credentials).status_code == 200
    response = client.get("/me")
    assert response.status_code == 200
    assert response.json() == {"username": credentials["username"]}

    assert client.post("/logout").status_code == 200
    assert client.get("/me").status_code == 401


def test_me_without_login_returns_401(client):
    response = client.get("/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "not logged in"}


def test_register_duplicate_username_returns_409(client, credentials):
    assert client.post("/register", json=credentials).status_code == 201
    assert client.post("/register", json=credentials).status_code == 409


def test_login_wrong_password_returns_401(client, credentials):
    client.post("/register", json=credentials)
    wrong = {**credentials, "password": "wrong-password"}
    assert client.post("/login", json=wrong).status_code == 401


def test_register_short_password_returns_422(client, credentials):
    short = {**credentials, "password": "123"}
    assert client.post("/register", json=short).status_code == 422
