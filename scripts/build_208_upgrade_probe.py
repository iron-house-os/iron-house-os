#!/usr/bin/env python3
"""Create and verify a Build 208 model-created schema for migration integration tests."""

from argparse import ArgumentParser
from uuid import uuid4

import app.models  # noqa: F401
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.schema_version import CURRENT_SCHEMA_REVISION
from app.db.session import engine
from app.models.document import Document
from app.models.equipment import Equipment
from app.models.project import Project
from app.models.rfq import RFQPackage, RFQPackageDocument, RFQPackageSupplierRecipient
from app.models.user import UserAccount

PROJECT_NUMBER = "BUILD-208-UPGRADE-PROBE"


def create_build_208_state() -> None:
    if inspect(engine).get_table_names():
        raise RuntimeError("Build 208 upgrade probe database must start empty.")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            UserAccount(
                email="build-208-legacy-role@example.com",
                display_name="Build 208 Legacy Role",
                role="administrator",
                password_hash="not-used-by-the-upgrade-probe",
            )
        )
        session.commit()
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE login_throttles"))
        connection.execute(text("ALTER TABLE user_accounts DROP COLUMN password_reset_required"))
    with Session(engine) as session:
        project = Project(
            name="Build 208 PostgreSQL upgrade probe",
            project_number=PROJECT_NUMBER,
            status="planning",
            metadata_json={"migration_probe": True},
        )
        rfq_package = RFQPackage(
            title="Build 208 legacy RFQ",
            status="planning",
            supplier_category_targets=[],
            metadata_json={},
        )
        rfq_package.recipients.append(
            RFQPackageSupplierRecipient(
                supplier_id=str(uuid4()),
                supplier_name="Build 208 Legacy Supplier",
                status="selected",
            )
        )
        rfq_package.documents.append(
            RFQPackageDocument(
                document_type="drawing",
                title="Build 208 legacy RFQ drawing",
                required=True,
                status="registered",
                storage_uri="s3://legacy/rfq-drawing.pdf",
                metadata_json={},
            )
        )
        session.add_all(
            [
                project,
                Document(
                    title="Build 208 legacy plan",
                    category="plans",
                    status="indexed",
                    metadata_json={},
                ),
                Equipment(name="Build 208 legacy excavator", status="operational"),
                rfq_package,
            ]
        )
        session.commit()
    if inspect(engine).has_table("alembic_version"):
        raise RuntimeError("Build 208 probe unexpectedly created an Alembic revision table.")


def verify_upgrade() -> None:
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        project = connection.execute(
            text("SELECT name, status FROM projects WHERE project_number = :project_number"),
            {"project_number": PROJECT_NUMBER},
        ).one()
        repaired_values = connection.execute(
            text(
                "SELECT "
                "(SELECT category FROM documents WHERE title = 'Build 208 legacy plan'), "
                "(SELECT status FROM documents WHERE title = 'Build 208 legacy plan'), "
                "(SELECT status FROM equipment WHERE name = 'Build 208 legacy excavator'), "
                "(SELECT status FROM rfq_packages WHERE title = 'Build 208 legacy RFQ'), "
                "(SELECT status FROM rfq_package_supplier_recipients WHERE supplier_name = 'Build 208 Legacy Supplier'), "
                "(SELECT status FROM rfq_package_documents WHERE title = 'Build 208 legacy RFQ drawing'), "
                "(SELECT role FROM user_accounts WHERE email = 'build-208-legacy-role@example.com')"
            )
        ).one()
    if revision != CURRENT_SCHEMA_REVISION:
        raise RuntimeError(
            f"Build 208 upgrade reached {revision}, expected {CURRENT_SCHEMA_REVISION}."
        )
    if tuple(project) != ("Build 208 PostgreSQL upgrade probe", "opportunity"):
        raise RuntimeError("Build 208 project data did not survive the migration.")
    expected = ("drawing", "registered", "available", "draft", "pending", "attached", "admin")
    if tuple(repaired_values) != expected:
        raise RuntimeError(
            f"Build 208 workflow values were not normalized: {tuple(repaired_values)} != {expected}."
        )


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("command", choices=("create", "verify"))
    args = parser.parse_args()
    if args.command == "create":
        create_build_208_state()
    else:
        verify_upgrade()
    print(f"Build 208 PostgreSQL upgrade probe {args.command} passed.")


if __name__ == "__main__":
    main()
