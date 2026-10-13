from flask import Blueprint, g, jsonify, request
from marshmallow import Schema, ValidationError, fields, validate

from auth import login_required
from models import db, Note

notes = Blueprint("notes", __name__)


def not_blank(value):
    if not value.strip():
        raise ValidationError("Must not be blank.")


class NoteSchema(Schema):
    id = fields.Integer(dump_only=True)
    title = fields.String(
        required=True,
        validate=[validate.Length(min=1, max=100), not_blank],
    )
    content = fields.String(
        required=True,
        validate=[validate.Length(min=1), not_blank],
    )
    user_id = fields.Integer(dump_only=True)


def load_note(partial=False):
    data = request.get_json()

    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")

    if partial and not data:
        raise ValueError("Provide at least one field to update.")

    return NoteSchema().load(data, partial=partial)


def owned_note(note_id):
    # Filter by ownership before returning any record.
    return db.first_or_404(
        db.select(Note).where(
            Note.id == note_id,
            Note.user_id == g.user.id,
        )
    )


def positive_parameter(name, default):
    raw = request.args.get(name)
    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a positive integer.")

    if value < 1:
        raise ValueError(f"{name} must be a positive integer.")

    return value


@notes.get("/notes")
@login_required
def list_notes():
    page = positive_parameter("page", 1)
    per_page = positive_parameter("per_page", 10)

    if per_page > 100:
        raise ValueError("per_page must not exceed 100.")

    result = db.paginate(
        db.select(Note)
        .where(Note.user_id == g.user.id)
        .order_by(Note.id),
        page=page,
        per_page=per_page,
        error_out=False,
    )

    return jsonify({
        "items": NoteSchema(many=True).dump(result.items),
        "page": result.page,
        "per_page": result.per_page,
        "total": result.total,
        "pages": result.pages,
        "has_next": result.has_next,
        "has_prev": result.has_prev,
    }), 200


@notes.get("/notes/<int:note_id>")
@login_required
def show_note(note_id):
    return jsonify(NoteSchema().dump(owned_note(note_id))), 200


@notes.post("/notes")
@login_required
def create_note():
    data = load_note()
    note = Note(**data, user_id=g.user.id)

    db.session.add(note)
    db.session.commit()

    return jsonify(NoteSchema().dump(note)), 201


@notes.patch("/notes/<int:note_id>")
@login_required
def update_note(note_id):
    note = owned_note(note_id)
    data = load_note(partial=True)

    for field, value in data.items():
        setattr(note, field, value)

    db.session.commit()
    return jsonify(NoteSchema().dump(note)), 200


@notes.delete("/notes/<int:note_id>")
@login_required
def delete_note(note_id):
    note = owned_note(note_id)

    db.session.delete(note)
    db.session.commit()

    return "", 204