from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops.agent.iron_house_agent.config import Project, load_settings, register_project
from tests.agent.conftest import write_registry


def test_load_settings_requires_production_approval_gate(tmp_path: Path) -> None:
    registry = write_registry(tmp_path, production_requires_owner_approval=False)

    with pytest.raises(ValueError, match="production_requires_owner_approval"):
        load_settings(registry)


def test_load_settings_rejects_public_dashboard_listener(tmp_path: Path) -> None:
    registry = write_registry(tmp_path, dashboard={"host": "0.0.0.0", "port": 8787})

    with pytest.raises(ValueError, match="loopback"):
        load_settings(registry)


def test_project_rejects_autonomous_production_deployment() -> None:
    project = Project(
        key="unsafe-project",
        name="Unsafe",
        repository="iron-house-os/unsafe",
        directory="unsafe",
        production_deploy_allowed=True,
    )

    with pytest.raises(ValueError, match="production deployment"):
        project.validate()


def test_registration_is_idempotent_and_preserves_safety_defaults(tmp_path: Path) -> None:
    registry = write_registry(tmp_path)
    project = Project(
        key="future-project",
        name="Future Project",
        repository="iron-house-os/future-project",
        directory="future-project",
    )

    first = register_project(registry, project)
    second = register_project(registry, project)

    assert len(first.projects) == 2
    assert len(second.projects) == 2
    saved = json.loads(registry.read_text(encoding="utf-8"))
    enrolled = next(item for item in saved["projects"] if item["key"] == project.key)
    assert enrolled["production_deploy_allowed"] is False
