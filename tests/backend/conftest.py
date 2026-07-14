from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import Request
from uuid import UUID

from app.api.dependencies.auth import require_authenticated_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import *  # noqa: F403
from app.services.auth import AuthenticatedUser

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_authenticated_user(request: Request) -> AuthenticatedUser:
    user = AuthenticatedUser(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        email="test-admin@ironhousecivil.com",
        display_name="Test Administrator",
        role="admin",
        session_version=1,
    )
    request.state.authenticated_user = user
    return user


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_authenticated_user] = override_authenticated_user
    yield
    app.dependency_overrides.clear()
