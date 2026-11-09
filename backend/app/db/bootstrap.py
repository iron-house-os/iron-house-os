import app.models  # noqa: F401

from app.db.base import Base
from app.db.session import engine


def bootstrap_schema() -> None:
    """Compatibility helper for local callers; deployed runtimes use Alembic."""

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    bootstrap_schema()
