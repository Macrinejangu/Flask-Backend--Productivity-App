from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates

db = SQLAlchemy()
bcrypt = Bcrypt()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    _password_hash = db.Column("password_hash", db.String(128), nullable=False)

    notes = db.relationship(
        "Note",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint(
            "length(trim(username)) BETWEEN 3 AND 50",
            name="username_length",
        ),
    )

    @validates("username")
    def validate_username(self, key, value):
        if not isinstance(value, str):
            raise ValueError("username must be a string.")

        value = value.strip().lower()
        if not 3 <= len(value) <= 50:
            raise ValueError("username must contain 3 to 50 characters.")

        return value

    @property
    def password_hash(self):
        raise AttributeError("Password hashes are private.")

    @password_hash.setter
    def password_hash(self, password):
        if not isinstance(password, str):
            raise ValueError("password must be a string.")

        if len(password) < 8:
            raise ValueError("password must contain at least 8 characters.")

        # bcrypt accepts at most 72 bytes, which differs from character count.
        if len(password.encode("utf-8")) > 72:
            raise ValueError("password must not exceed 72 UTF-8 bytes.")

        self._password_hash = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

    def authenticate(self, password):
        if not isinstance(password, str):
            return False
        if len(password.encode("utf-8")) > 72:
            return False

        return bcrypt.check_password_hash(self._password_hash, password)


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
    )

    user = db.relationship("User", back_populates="notes")

    __table_args__ = (
        db.CheckConstraint(
            "length(trim(title)) BETWEEN 1 AND 100",
            name="note_title_length",
        ),
        db.CheckConstraint(
            "length(trim(content)) > 0",
            name="note_content_not_blank",
        ),
    )

    @validates("title", "content")
    def validate_text(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string.")

        value = value.strip()

        if key == "title" and len(value) > 100:
            raise ValueError("title must contain at most 100 characters.")

        return value