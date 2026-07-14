import app.models  # noqa: F401

from app.db.base import Base
from app.db.session import engine


def bootstrap_schema() -> None:
    """Create model-backed tables when a deployment has no Alembic baseline yet."""

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    bootstrap_schema()
