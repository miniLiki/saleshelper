from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import document, user  # noqa: F401
from app.services.bootstrap import seed_defaults


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_defaults(db)


if __name__ == "__main__":
    init_db()
