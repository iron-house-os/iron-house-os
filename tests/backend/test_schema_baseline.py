from pathlib import Path
from uuid import uuid4

import app.models  # noqa: F401
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.db.schema_version import CURRENT_SCHEMA_REVISION
from app.models.project import Project

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"


def _upgrade_to_head(monkeypatch: pytest.MonkeyPatch, database_url: str) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(config, "head")
    get_settings.cache_clear()


def test_baseline_creates_current_schema_from_empty_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'fresh.db'}"

    _upgrade_to_head(monkeypatch, database_url)

    engine = create_engine(database_url)
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        differences = compare_metadata(
            MigrationContext.configure(connection, opts={"compare_type": True}),
            Base.metadata,
        )
    assert revision == CURRENT_SCHEMA_REVISION
    assert differences == []


def test_baseline_adopts_complete_build_208_schema_without_losing_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'build-208.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    project_id = uuid4()
    with Session(engine) as session:
        session.add(
            Project(
                id=project_id,
                name="Build 208 preserved project",
                project_number="BUILD-208-PRESERVED",
                metadata_json={"source": "pre-migration"},
            )
        )
        session.commit()

    _upgrade_to_head(monkeypatch, database_url)

    with engine.connect() as connection:
        stored_name = connection.execute(
            text("SELECT name FROM projects WHERE id = :project_id"),
            {"project_id": project_id.hex},
        ).scalar_one()
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert stored_name == "Build 208 preserved project"
    assert revision == CURRENT_SCHEMA_REVISION


def test_baseline_rejects_partial_unversioned_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'partial.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id VARCHAR(32) PRIMARY KEY, name VARCHAR(255))"))

    with pytest.raises(RuntimeError, match="partial unversioned"):
        _upgrade_to_head(monkeypatch, database_url)

    assert inspect(engine).has_table("projects")
