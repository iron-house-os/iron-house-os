import app.models  # noqa: F401
from sqlalchemy import create_engine, text

from app.db.base import Base
from app.db.schema_version import CURRENT_SCHEMA_REVISION
from app.services import system_readiness


def test_runtime_readiness_probes_database_and_storage(monkeypatch) -> None:
    monkeypatch.setattr(system_readiness, "_database_readiness", lambda: (True, "ready"))
    monkeypatch.setattr(system_readiness, "_storage_readiness", lambda: (True, "ready"))

    readiness = system_readiness.get_system_readiness(probe_runtime=True)

    assert readiness["status"] == "ready"
    assert readiness["checks"]["database"] == "ready"
    assert readiness["checks"]["document_storage"] == "ready"


def test_runtime_readiness_fails_when_a_dependency_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        system_readiness,
        "_database_readiness",
        lambda: (False, "unavailable"),
    )
    monkeypatch.setattr(system_readiness, "_storage_readiness", lambda: (True, "ready"))

    readiness = system_readiness.get_system_readiness(probe_runtime=True)

    assert readiness["status"] == "not_ready"
    assert readiness["checks"]["database"] == "unavailable"


def test_database_readiness_requires_current_alembic_revision(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('outdated')"))
    monkeypatch.setattr(system_readiness, "engine", engine)

    assert system_readiness._database_readiness() == (False, "migration_required")

    with engine.begin() as connection:
        connection.execute(
            text("UPDATE alembic_version SET version_num = :revision"),
            {"revision": CURRENT_SCHEMA_REVISION},
        )
    assert system_readiness._database_readiness() == (True, "ready")


def test_database_readiness_rejects_legacy_tender_status(monkeypatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version VALUES (:revision)"),
            {"revision": CURRENT_SCHEMA_REVISION},
        )
        connection.execute(
            text(
                "INSERT INTO tenders (id, title, status, metadata_json, created_at, updated_at) "
                "VALUES ('00000000000000000000000000000001', 'Legacy', 'watching', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
    monkeypatch.setattr(system_readiness, "engine", engine)

    assert system_readiness._database_readiness() == (False, "invalid_tender_status")
