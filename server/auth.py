from functools import wraps

from flask import Blueprint, g, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from models import db, User

auth = Blueprint("auth", __name__)


def user_data(user):
    # Explicit fields keep password hashes out of API responses.
    return {"id": user.id, "username": user.username}


def read_credentials():
    data = request.get_json()

    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")

    if set(data) - {"username", "password"}:
        raise ValueError("Unexpected fields.")

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not username.strip():
        raise ValueError("username is required.")

    if not isinstance(password, str) or not password:
        raise ValueError("password is required.")

    return username.strip().lower(), password


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id is not None else None

        if user is None:
            session.clear()
            return jsonify({"error": "Authentication required."}), 401

        g.user = user
        return view(*args, **kwargs)

    return wrapped


@auth.post("/signup")
def signup():
    username, password = read_credentials()
    user = User(username=username)
    user.password_hash = password

    try:
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Username is unavailable."}), 409

    session.clear()
    session["user_id"] = user.id

    return jsonify(user_data(user)), 201


@auth.post("/login")
def login():
    username, password = read_credentials()
    user = db.session.execute(
        db.select(User).where(User.username == username)
    ).scalar_one_or_none()

    if user is None or not user.authenticate(password):
        return jsonify({"error": "Invalid username or password."}), 401

    session.clear()
    session["user_id"] = user.id

    return jsonify(user_data(user)), 200


@auth.delete("/logout")
def logout():
    session.clear()
    return "", 204


@auth.get("/check_session")
@login_required
def check_session():
    return jsonify(user_data(g.user)), 200