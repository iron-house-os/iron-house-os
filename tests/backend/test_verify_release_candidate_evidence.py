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
