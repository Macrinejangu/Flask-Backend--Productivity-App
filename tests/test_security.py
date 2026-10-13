import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

from app import create_app
from models import db


@pytest.fixture
def client():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "security-test-only",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "BCRYPT_LOG_ROUNDS": 4,
        "CSRF_ENABLED": True,
    })

    with app.app_context():
        db.create_all()

    yield app.test_client()

    with app.app_context():
        db.session.remove()
        db.drop_all()


def credentials():
    return {"username": "cate", "password": "StudyPass123!"}


def test_missing_token_rejected(client):
    response = client.post("/signup", json=credentials())
    assert response.status_code == 403


def test_wrong_token_rejected(client):
    client.get("/csrf-token")
    response = client.post(
        "/signup",
        json=credentials(),
        headers={"X-CSRF-Token": "wrong"},
    )
    assert response.status_code == 403


def test_token_refresh_and_protected_creation(client):
    token = client.get("/csrf-token").get_json()["csrf_token"]

    response = client.post(
        "/signup",
        json=credentials(),
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 201

    body = {"title": "Private", "content": "My note"}

    assert client.post(
        "/notes",
        json=body,
        headers={"X-CSRF-Token": token},
    ).status_code == 403

    fresh = client.get("/csrf-token").get_json()["csrf_token"]
    assert fresh != token

    response = client.post(
        "/notes",
        json=body,
        headers={"X-CSRF-Token": fresh},
    )
    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"


def test_token_from_another_session_rejected(client):
    other = client.application.test_client()
    token = other.get("/csrf-token").get_json()["csrf_token"]

    response = client.post(
        "/signup",
        json=credentials(),
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 403