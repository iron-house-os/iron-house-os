import json

from app.db.session import SessionLocal
from app.services.backups import run_daily_controller


def main() -> int:
    with SessionLocal() as db:
        result = run_daily_controller(db)
    print(json.dumps(result.model_dump()))
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
