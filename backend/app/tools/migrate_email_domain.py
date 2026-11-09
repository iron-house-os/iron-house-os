"""Dry-run or apply the controlled Iron House operational email-domain migration."""

from argparse import ArgumentParser
import json

from app.db.session import SessionLocal
from app.services.email_domain_migration import (
    CANONICAL_EMAIL_DOMAIN,
    EmailDomainMigrationConflict,
    LEGACY_EMAIL_DOMAIN,
    migrate_email_domain,
)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--from-domain", default=LEGACY_EMAIL_DOMAIN)
    parser.add_argument("--to-domain", default=CANONICAL_EMAIL_DOMAIN)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--confirm",
        help="Required with --apply; must exactly match --to-domain.",
    )
    args = parser.parse_args()
    if args.apply and args.confirm != args.to_domain:
        raise SystemExit("--apply requires --confirm matching --to-domain exactly.")

    with SessionLocal() as db:
        try:
            report = migrate_email_domain(
                db,
                from_domain=args.from_domain,
                to_domain=args.to_domain,
                apply=args.apply,
            )
            if args.apply:
                db.commit()
            else:
                db.rollback()
        except EmailDomainMigrationConflict as exc:
            db.rollback()
            print(json.dumps({"status": "blocked", "conflicts": exc.conflicts}, indent=2))
            raise SystemExit(2) from exc

    print(json.dumps({"status": "applied" if args.apply else "dry_run", **report.to_dict()}, indent=2))


if __name__ == "__main__":
    main()
