from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
MANIFEST = SCRIPTS / "recovery_manifest.py"
RETENTION = SCRIPTS / "backup_retention.py"


def _bundle(root: Path, name: str, created_at: str) -> Path:
    bundle = root / name
    bundle.mkdir()
    (bundle / "database.dump").write_bytes(f"database-{name}".encode())
    (bundle / "backend-data.tar.gz").write_bytes(f"uploads-{name}".encode())
    subprocess.run(
        [
            sys.executable,
            str(MANIFEST),
            "create",
            "--directory",
            str(bundle),
            "--schema-revision",
            "20260714_0002",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["created_at"] = created_at
    manifest_path.write_text(json.dumps(manifest))
    return bundle


def test_retention_verifies_all_bundles_before_pruning(tmp_path: Path) -> None:
    newest = _bundle(tmp_path, "newest", "2026-07-14T00:00:00+00:00")
    recent = _bundle(tmp_path, "recent", "2026-07-10T00:00:00+00:00")
    old = _bundle(tmp_path, "old", "2026-05-01T00:00:00+00:00")

    result = subprocess.run(
        [
            sys.executable,
            str(RETENTION),
            "--root",
            str(tmp_path),
            "--retention-days",
            "30",
            "--keep-minimum",
            "1",
            "--maximum-bundles",
            "3",
            "--now",
            datetime(2026, 7, 14, tzinfo=UTC).isoformat(),
            "--apply",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    assert report["verified_bundles"] == 3
    assert report["deleted"] == ["old"]
    assert newest.is_dir()
    assert recent.is_dir()
    assert not old.exists()


def test_retention_aborts_without_deleting_when_a_bundle_is_corrupt(tmp_path: Path) -> None:
    newest = _bundle(tmp_path, "newest", "2026-07-14T00:00:00+00:00")
    old = _bundle(tmp_path, "old", "2026-05-01T00:00:00+00:00")
    (newest / "database.dump").write_bytes(b"corrupt")

    result = subprocess.run(
        [
            sys.executable,
            str(RETENTION),
            "--root",
            str(tmp_path),
            "--retention-days",
            "30",
            "--keep-minimum",
            "1",
            "--maximum-bundles",
            "3",
            "--now",
            "2026-07-14T00:00:00+00:00",
            "--apply",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert newest.is_dir()
    assert old.is_dir()
