from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.release_candidate_evidence import build_evidence  # noqa: E402
from scripts.verify_release_candidate_evidence import verify_evidence  # noqa: E402


def _write_evidence(tmp_path: Path, evidence: dict[str, object]) -> Path:
    import json

    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return path


def test_verifier_accepts_bound_release_with_all_required_gates(tmp_path: Path) -> None:
    release_sha = "a" * 40
    evidence = build_evidence(
        ROOT,
        release_id=release_sha,
        gates={
            "ci": "passed",
            "browser_mobile_accessibility": "passed",
            "production_stack_smoke": "passed",
            "backup_restore": "passed",
        },
    )
    evidence["commit_sha"] = release_sha
    evidence["working_tree_clean"] = True

    verified = verify_evidence(ROOT, _write_evidence(tmp_path, evidence), release_sha)

    assert verified["commit_sha"] == release_sha


def test_verifier_rejects_pending_gate(tmp_path: Path) -> None:
    release_sha = "b" * 40
    evidence = build_evidence(
        ROOT,
        release_id=release_sha,
        gates={
            "ci": "passed",
            "browser_mobile_accessibility": "not_run",
            "production_stack_smoke": "passed",
            "backup_restore": "passed",
        },
    )
    evidence["commit_sha"] = release_sha
    evidence["working_tree_clean"] = True

    with pytest.raises(ValueError, match="browser_mobile_accessibility"):
        verify_evidence(ROOT, _write_evidence(tmp_path, evidence), release_sha)


def test_verifier_rejects_integrity_mismatch(tmp_path: Path) -> None:
    release_sha = "c" * 40
    evidence = build_evidence(
        ROOT,
        release_id=release_sha,
        gates={gate: "passed" for gate in (
            "ci",
            "browser_mobile_accessibility",
            "production_stack_smoke",
            "backup_restore",
        )},
    )
    evidence["commit_sha"] = release_sha
    evidence["working_tree_clean"] = True
    evidence["files"]["docker-compose.production.yml"] = "0" * 64

    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_evidence(ROOT, _write_evidence(tmp_path, evidence), release_sha)


def test_staging_verifier_requires_immutable_runtime_and_rollback_evidence(
    tmp_path: Path,
) -> None:
    release_sha = "d" * 40
    evidence = build_evidence(
        ROOT,
        release_id=release_sha,
        gates={
            gate: "passed"
            for gate in (
                "staging_configuration",
                "staging_smoke",
                "role_denial",
                "synthetic_data",
                "backup_restore",
                "rollback",
            )
        },
        environment="staging",
        images={
            "backend": "sha256:" + "1" * 64,
            "frontend": "sha256:" + "2" * 64,
            "postgres": "sha256:" + "3" * 64,
        },
        migrations={"alembic": "build_237"},
        rollback="passed",
        production_baseline="55afaa689603263c1ad415436e90cce6679808c3",
    )
    evidence["commit_sha"] = release_sha
    evidence["working_tree_clean"] = True

    verified = verify_evidence(
        ROOT,
        _write_evidence(tmp_path, evidence),
        release_sha,
        profile="staging",
    )

    assert verified["environment"] == "staging"


def test_staging_verifier_rejects_non_immutable_image_reference(tmp_path: Path) -> None:
    release_sha = "e" * 40
    evidence = build_evidence(
        ROOT,
        release_id=release_sha,
        gates={
            gate: "passed"
            for gate in (
                "staging_configuration",
                "staging_smoke",
                "role_denial",
                "synthetic_data",
                "backup_restore",
                "rollback",
            )
        },
        environment="staging",
        images={"backend": "latest", "frontend": "sha256:2", "postgres": "sha256:3"},
        migrations={"alembic": "build_237"},
        rollback="passed",
        production_baseline="55afaa689603263c1ad415436e90cce6679808c3",
    )
    evidence["commit_sha"] = release_sha
    evidence["working_tree_clean"] = True

    with pytest.raises(ValueError, match="Immutable staging image IDs"):
        verify_evidence(
            ROOT,
            _write_evidence(tmp_path, evidence),
            release_sha,
            profile="staging",
        )
