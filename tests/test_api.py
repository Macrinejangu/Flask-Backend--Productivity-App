import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

from app import create_app
from models import db, User


@pytest.fixture
def application():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "BCRYPT_LOG_ROUNDS": 4,
        "CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


def signup(client, username="cate"):
    response = client.post("/signup", json={
        "username": username,
        "password": "StudyPass123!",
    })
    assert response.status_code == 201
    return response.get_json()


def create_note(client, title="Study"):
    response = client.post("/notes", json={
        "title": title,
        "content": "Review authentication.",
    })
    assert response.status_code == 201
    return response.get_json()


def test_auth_flow(application):
    client = application.test_client()

    assert client.get("/check_session").status_code == 401
    user = signup(client)
    assert set(user) == {"id", "username"}
    assert client.get("/check_session").get_json() == user

    assert client.delete("/logout").status_code == 204
    assert client.get("/check_session").status_code == 401

    assert client.post("/login", json={
        "username": "cate",
        "password": "wrong",
    }).status_code == 401

    assert client.post("/login", json={
        "username": "cate",
        "password": "StudyPass123!",
    }).status_code == 200


def test_unique_normalized_username(application):
    client = application.test_client()
    signup(client)

    response = client.post("/signup", json={
        "username": " CATE ",
        "password": "AnotherPass123!",
    })
    assert response.status_code == 409


def test_password_protection(application):
    client = application.test_client()
    signup(client)

    with application.app_context():
        user = db.session.execute(db.select(User)).scalar_one()
        assert user._password_hash != "StudyPass123!"
        assert user.authenticate("StudyPass123!")
        with pytest.raises(AttributeError):
            user.password_hash


@pytest.mark.parametrize("method,path", [
    ("get", "/notes"),
    ("get", "/notes/1"),
    ("post", "/notes"),
    ("patch", "/notes/1"),
    ("delete", "/notes/1"),
])
def test_anonymous_access(application, method, path):
    client = application.test_client()
    response = getattr(client, method)(path)
    assert response.status_code == 401


def test_note_crud(application):
    client = application.test_client()
    user = signup(client)
    note = create_note(client)

    assert note["user_id"] == user["id"]
    path = f"/notes/{note['id']}"

    assert client.get(path).get_json()["title"] == "Study"

    response = client.patch(path, json={"title": "Updated"})
    assert response.status_code == 200
    assert response.get_json()["content"] == note["content"]

    response = client.delete(path)
    assert response.status_code == 204
    assert response.data == b""
    assert client.get(path).status_code == 404


def test_cross_user_isolation(application):
    owner = application.test_client()
    stranger = application.test_client()

    signup(owner, "owner")
    note = create_note(owner)
    signup(stranger, "stranger")

    path = f"/notes/{note['id']}"

    assert stranger.get("/notes").get_json()["total"] == 0
    assert stranger.get(path).status_code == 404
    assert stranger.patch(
        path, json={"title": "Stolen"}
    ).status_code == 404
    assert stranger.delete(path).status_code == 404
    assert owner.get(path).get_json()["title"] == "Study"


def test_reject_forged_owner(application):
    client = application.test_client()
    signup(client)

    response = client.post("/notes", json={
        "title": "Forged",
        "content": "Invalid owner.",
        "user_id": 999,
    })

    assert response.status_code == 400
    assert client.get("/notes").get_json()["total"] == 0


def test_pagination_is_user_scoped(application):
    owner = application.test_client()
    other = application.test_client()

    signup(owner, "owner")
    for number in range(3):
        create_note(owner, title=f"Note {number}")

    signup(other, "other")
    create_note(other)

    first = owner.get("/notes?page=1&per_page=2").get_json()
    second = owner.get("/notes?page=2&per_page=2").get_json()

    assert first["total"] == 3
    assert first["pages"] == 2
    assert len(first["items"]) == 2
    assert first["has_next"] is True
    assert len(second["items"]) == 1
    assert second["has_prev"] is True


@pytest.mark.parametrize("query", [
    "page=0",
    "page=abc",
    "per_page=-1",
    "per_page=101",
])
def test_invalid_pagination(application, query):
    client = application.test_client()
    signup(client)

    assert client.get(f"/notes?{query}").status_code == 400


def test_invalid_update_preserves_note(application):
    client = application.test_client()
    signup(client)
    note = create_note(client)
    path = f"/notes/{note['id']}"

    response = client.patch(
        path, json={"title": "Changed", "content": " "}
    )

    assert response.status_code == 400
    assert client.get(path).get_json() == note