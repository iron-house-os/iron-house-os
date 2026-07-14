from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.user import UserAccount
from app.services.auth import hash_password, normalize_email


def bootstrap_admin() -> bool:
    settings = get_settings()
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        if settings.environment.lower() == "production":
            raise RuntimeError(
                "BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD are required in production."
            )
        return False
    email = normalize_email(settings.bootstrap_admin_email)
    with SessionLocal() as db:
        existing = db.scalar(select(UserAccount).where(func.lower(UserAccount.email) == email))
        if existing is not None:
            return False
        db.add(
            UserAccount(
                email=email,
                display_name=settings.bootstrap_admin_name.strip() or "Iron House Administrator",
                role="admin",
                password_hash=hash_password(settings.bootstrap_admin_password),
                is_active=True,
                session_version=1,
            )
        )
        db.commit()
    return True


if __name__ == "__main__":
    created = bootstrap_admin()
    print("Created the bootstrap administrator." if created else "Bootstrap administrator unchanged.")
