import json

from app.db.session import SessionLocal
from app.services.backups import run_daily_controller


def main() -> None:
    with SessionLocal() as db:
        result = run_daily_controller(db)
    print(json.dumps(result.model_dump(), sort_keys=True))


if __name__ == "__main__":
    main()
