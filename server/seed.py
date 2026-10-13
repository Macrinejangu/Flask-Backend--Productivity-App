from app import app
from models import db, User, Note


def seed_database():
    with app.app_context():
        # Delete child records before their owners.
        Note.query.delete()
        User.query.delete()

        cate = User(username="cate")
        cate.password_hash = "StudyPass123!"

        alex = User(username="alex")
        alex.password_hash = "NotesPass123!"

        notes = [
            Note(
                title="Study plan",
                content="Review Flask authentication and pagination.",
                user=cate,
            ),
            Note(
                title="Weekly goals",
                content="Complete the productivity app backend.",
                user=cate,
            ),
            Note(
                title="Reading list",
                content="Read about SQLAlchemy relationships.",
                user=alex,
            ),
        ]

        db.session.add_all([cate, alex, *notes])
        db.session.commit()

        assert cate.authenticate("StudyPass123!")
        assert alex.authenticate("NotesPass123!")
        assert len(cate.notes) == 2
        assert len(alex.notes) == 1

        print(
            f"Seeded {User.query.count()} users "
            f"and {Note.query.count()} notes."
        )


if __name__ == "__main__":
    seed_database()