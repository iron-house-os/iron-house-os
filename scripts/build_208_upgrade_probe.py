#!/usr/bin/env python3
"""Create and verify a Build 208 model-created schema for migration integration tests."""

from argparse import ArgumentParser

import app.models  # noqa: F401
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.schema_version import CURRENT_SCHEMA_REVISION
from app.db.session import engine
from app.models.project import Project

PROJECT_NUMBER = "BUILD-208-UPGRADE-PROBE"


def create_build_208_state() -> None:
    if inspect(engine).get_table_names():
        raise RuntimeError("Build 208 upgrade probe database must start empty.")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            Project(
                name="Build 208 PostgreSQL upgrade probe",
                project_number=PROJECT_NUMBER,
                metadata_json={"migration_probe": True},
            )
        )
        session.commit()
    if inspect(engine).has_table("alembic_version"):
        raise RuntimeError("Build 208 probe unexpectedly created an Alembic revision table.")


def verify_upgrade() -> None:
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        project = connection.execute(
            text("SELECT name FROM projects WHERE project_number = :project_number"),
            {"project_number": PROJECT_NUMBER},
        ).scalar_one()
    if revision != CURRENT_SCHEMA_REVISION:
        raise RuntimeError(f"Build 208 upgrade reached {revision}, expected {CURRENT_SCHEMA_REVISION}.")
    if project != "Build 208 PostgreSQL upgrade probe":
        raise RuntimeError("Build 208 project data did not survive the migration.")


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
