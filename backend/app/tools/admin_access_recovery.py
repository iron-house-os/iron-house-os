"""Protected server-console inspection, recovery and cutover-readiness commands."""

from argparse import ArgumentParser
from getpass import getpass
import json

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.admin_access_recovery import (
    AdminAccessRecoveryBlocked,
    inspect_admin_recovery,
    inspect_identity_cutover,
    recover_admin_access,
)


def _parser() -> ArgumentParser:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--email", required=True)

    recover_parser = subparsers.add_parser("recover")
    recover_parser.add_argument("--email", required=True)
    recover_parser.add_argument("--confirm-account-id", required=True)
    recover_parser.add_argument("--reason", required=True)
    recover_parser.add_argument("--operator", required=True)
    recover_parser.add_argument("--apply", action="store_true")

    verify_parser = subparsers.add_parser("verify-cutover")
    verify_parser.add_argument("--email", required=True)
    return parser


def _temporary_password() -> str:
    first = getpass("New temporary password: ")
    second = getpass("Repeat temporary password: ")
    if first != second:
        raise AdminAccessRecoveryBlocked(["The temporary passwords do not match."])
    return first


def main() -> None:
    args = _parser().parse_args()
    settings = get_settings()
    with SessionLocal() as db:
        try:
            if args.command == "inspect":
                result = inspect_admin_recovery(db, args.email)
                payload = {"status": "eligible" if result.eligible else "blocked", **result.to_dict()}
                db.rollback()
            elif args.command == "verify-cutover":
                result = inspect_identity_cutover(
                    db,
                    canonical_admin_email=args.email,
                    configured_bootstrap_email=settings.bootstrap_admin_email,
                )
                payload = {"status": "ready" if result.ready else "blocked", **result.to_dict()}
                db.rollback()
            else:
                if not args.apply:
                    raise AdminAccessRecoveryBlocked(["The recover command requires --apply."])
                evidence = recover_admin_access(
                    db,
                    email=args.email,
                    confirm_account_id=args.confirm_account_id,
                    new_password=_temporary_password(),
                    reason=args.reason,
                    operator=args.operator,
                )
                db.commit()
                payload = {"status": "applied", **evidence.to_dict()}
        except AdminAccessRecoveryBlocked as exc:
            db.rollback()
            print(json.dumps({"status": "blocked", "issues": exc.issues}, indent=2))
            raise SystemExit(2) from exc
        except ValueError as exc:
            db.rollback()
            print(json.dumps({"status": "blocked", "issues": [str(exc)]}, indent=2))
            raise SystemExit(2) from exc
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
