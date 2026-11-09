from pathlib import Path
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "recovery_manifest.py"


def _run(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        check=check,
        capture_output=True,
        text=True,
    )


def test_recovery_manifest_verifies_bundle_and_rejects_corruption(tmp_path: Path) -> None:
    (tmp_path / "database.dump").write_bytes(b"database snapshot")
    (tmp_path / "backend-data.tar.gz").write_bytes(b"upload snapshot")

    _run(
        "create",
        "--directory",
        str(tmp_path),
        "--schema-revision",
        "20260714_0001",
    )
    _run("verify", "--directory", str(tmp_path))

    (tmp_path / "database.dump").write_bytes(b"corrupted snapshot")
    result = _run("verify", "--directory", str(tmp_path), check=False)

    assert result.returncode != 0
    assert "mismatch" in result.stderr
