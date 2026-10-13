import os
import sqlite3

from flask import Flask, jsonify
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine

from models import db, bcrypt, User, Note

from werkzeug.exceptions import HTTPException
from auth import auth

from marshmallow import ValidationError
from notes import notes

@event.listens_for(Engine, "connect")
def enable_foreign_keys(connection, connection_record):
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///app.db"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    bcrypt.init_app(app)
    Migrate(app, db)

    app.register_blueprint(auth)

    app.register_blueprint(notes)

    @app.errorhandler(ValidationError)
    def schema_error(error):
        db.session.rollback()
        return jsonify({"errors": error.messages}), 400

    @app.errorhandler(ValueError)
    def invalid_input(error):
        db.session.rollback()
        return jsonify({"error": str(error)}), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify({"error": error.description}), error.code

    @app.get("/")
    def home():
        return jsonify({"message": "Private Notes API"}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=5555, debug=True)