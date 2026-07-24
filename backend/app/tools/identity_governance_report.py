"""Generate secret-safe identity governance evidence for scheduled operations."""

from argparse import ArgumentParser
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.db.session import SessionLocal
from app.services.identity_governance import build_identity_governance_snapshot

SEVERITY_RANK = {"normal": 1, "high": 2, "critical": 3}


def _parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--fail-on",
        choices=["never", "normal", "high", "critical"],
        default="critical",
        help="Return exit code 3 when a finding reaches this severity.",
    )
    return parser


def evidence_envelope(payload: dict) -> dict:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {
        "evidence_type": "identity_governance_snapshot",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": hashlib.sha256(canonical).hexdigest(),
        "snapshot": payload,
    }


def exit_code_for_findings(findings: list[dict], fail_on: str) -> int:
    if fail_on == "never":
        return 0
    threshold = SEVERITY_RANK[fail_on]
    return 3 if any(SEVERITY_RANK[finding["severity"]] >= threshold for finding in findings) else 0


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def main() -> None:
    args = _parser().parse_args()
    with SessionLocal() as db:
        snapshot = build_identity_governance_snapshot(db)
        db.rollback()
    payload = snapshot.model_dump(mode="json")
    envelope = evidence_envelope(payload)
    rendered = json.dumps(envelope, indent=2) + "\n"
    if args.output:
        _write_atomic(args.output, rendered)
    else:
        print(rendered, end="")
    raise SystemExit(exit_code_for_findings(payload["findings"], args.fail_on))


if __name__ == "__main__":
    main()
