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
from app.models.document import Document
from app.models.equipment import Equipment
from app.models.rfq import RFQPackage, RFQPackageDocument, RFQPackageSupplierRecipient
from app.models.tender import Tender
from app.models.user import UserAccount

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
    user_id = uuid4()
    with Session(engine) as session:
        session.add(
            UserAccount(
                id=user_id,
                email="legacy-role@example.com",
                display_name="Legacy Role",
                role="administrator",
                password_hash="not-used-by-this-migration-test",
            )
        )
        session.commit()
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE login_throttles"))
        connection.execute(text("ALTER TABLE user_accounts DROP COLUMN password_reset_required"))
    project_id = uuid4()
    tender_id = uuid4()
    document_id = uuid4()
    equipment_id = uuid4()
    rfq_package_id = uuid4()
    recipient_id = uuid4()
    rfq_document_id = uuid4()
    with Session(engine) as session:
        session.add_all(
            [
                Project(
                    id=project_id,
                    name="Build 208 preserved project",
                    project_number="BUILD-208-PRESERVED",
                    status="planning",
                    metadata_json={"source": "pre-migration"},
                ),
                Tender(
                    id=tender_id,
                    title="Phase 1 watching tender",
                    tender_number="PHASE-1-WATCHING",
                    status="watching",
                    metadata_json={},
                ),
                Document(
                    id=document_id,
                    title="Legacy plan",
                    category="plans",
                    status="indexed",
                    metadata_json={},
                ),
                Equipment(
                    id=equipment_id,
                    name="Legacy active excavator",
                    status="operational",
                ),
                RFQPackage(
                    id=rfq_package_id,
                    title="Legacy package",
                    status="planning",
                    supplier_category_targets=[],
                    metadata_json={},
                ),
                RFQPackageSupplierRecipient(
                    id=recipient_id,
                    rfq_package_id=rfq_package_id,
                    supplier_id="legacy-supplier",
                    supplier_name="Legacy Supplier",
                    status="selected",
                ),
                RFQPackageDocument(
                    id=rfq_document_id,
                    rfq_package_id=rfq_package_id,
                    document_type="drawing",
                    title="Legacy attachment",
                    required=True,
                    status="registered",
                    storage_uri="s3://legacy/attachment.pdf",
                    metadata_json={},
                ),
            ]
        )
        session.commit()

    _upgrade_to_head(monkeypatch, database_url)

    with engine.connect() as connection:
        stored_name = connection.execute(
            text("SELECT name FROM projects WHERE id = :project_id"),
            {"project_id": project_id.hex},
        ).scalar_one()
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        repaired_tender_status = connection.execute(
            text("SELECT status FROM tenders WHERE id = :tender_id"),
            {"tender_id": tender_id.hex},
        ).scalar_one()
        repaired_values = connection.execute(
            text(
                "SELECT "
                "(SELECT status FROM projects WHERE id = :project_id), "
                "(SELECT category FROM documents WHERE id = :document_id), "
                "(SELECT status FROM documents WHERE id = :document_id), "
                "(SELECT status FROM equipment WHERE id = :equipment_id), "
                "(SELECT status FROM rfq_packages WHERE id = :rfq_package_id), "
                "(SELECT status FROM rfq_package_supplier_recipients WHERE id = :recipient_id), "
                "(SELECT status FROM rfq_package_documents WHERE id = :rfq_document_id), "
                "(SELECT role FROM user_accounts WHERE id = :user_id)"
            ),
            {
                "project_id": project_id.hex,
                "document_id": document_id.hex,
                "equipment_id": equipment_id.hex,
                "rfq_package_id": rfq_package_id.hex,
                "recipient_id": recipient_id.hex,
                "rfq_document_id": rfq_document_id.hex,
                "user_id": user_id.hex,
            },
        ).one()
    assert stored_name == "Build 208 preserved project"
    assert repaired_tender_status == "new"
    assert tuple(repaired_values) == (
        "opportunity",
        "drawing",
        "registered",
        "available",
        "draft",
        "pending",
        "attached",
        "admin",
    )
    assert revision == CURRENT_SCHEMA_REVISION


def test_baseline_rejects_partial_unversioned_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'partial.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE projects (id VARCHAR(32) PRIMARY KEY, name VARCHAR(255))")
        )

    with pytest.raises(RuntimeError, match="partial unversioned"):
        _upgrade_to_head(monkeypatch, database_url)

    assert inspect(engine).has_table("projects")
