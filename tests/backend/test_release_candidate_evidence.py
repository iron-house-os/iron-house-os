from datetime import UTC, datetime
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.release_candidate_evidence import build_evidence, parse_gates, render_markdown  # noqa: E402


def test_release_candidate_evidence_is_bound_to_commit_and_files() -> None:
    generated_at = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    evidence = build_evidence(
        ROOT,
        release_id="build-215-test",
        gates={"backup_restore": "passed", "ci": "not_run"},
        generated_at=generated_at,
    )

    assert evidence["release_id"] == "build-215-test"
    assert len(str(evidence["commit_sha"])) == 40
    assert len(str(evidence["commit_tree"])) == 40
    assert evidence["generated_at"] == "2026-07-14T12:00:00+00:00"
    assert evidence["operator_acceptance"] == "pending"
    assert len(evidence["files"]["docker-compose.production.yml"]) == 64
    markdown = render_markdown(evidence)
    assert "Operator acceptance: **pending**" in markdown
    assert "backup_restore: **passed**" in markdown


def test_incomplete_release_package_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Release package is incomplete"):
        build_evidence(tmp_path, release_id=None, gates={})


def test_gate_parser_rejects_unknown_outcomes() -> None:
    assert parse_gates(["ci=passed", "browser=not_run"]) == {
        "browser": "not_run",
        "ci": "passed",
    }
    with pytest.raises(ValueError, match="Invalid gate"):
        parse_gates(["ci=probably"])
