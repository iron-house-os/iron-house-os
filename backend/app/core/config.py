from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Iron House OS API"
    environment: str = "development"
    release_id: str = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://iron_house:iron_house_dev@localhost:5432/iron_house_os"
    secret_key: str = Field(default="change-me-in-development", min_length=16)
    access_token_expire_minutes: int = 480
    session_cookie_name: str = "ihos_session"
    session_cookie_secure: bool = False
    login_max_failed_attempts: int = Field(default=5, ge=3, le=20)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440)
    login_ip_max_failed_attempts: int = Field(default=15, ge=3, le=100)
    login_ip_lockout_minutes: int = Field(default=15, ge=1, le=1440)
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_admin_name: str = "Iron House Administrator"
    backend_cors_origins: list[str] = ["http://localhost:5173"]
    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-5.6-sol"
    openai_transcription_model: str = "gpt-4o-mini-transcribe"
    openai_api_base_url: str = "https://api.openai.com/v1"
    iron_house_chat_enabled: bool = True
    meeting_minutes_enabled: bool = True
    google_calendar_enabled: bool = False
    google_calendar_client_id: str | None = None
    google_calendar_client_secret: str | None = None
    google_calendar_redirect_uri: str = (
        "http://localhost:8000/api/v1/google-calendar/oauth/callback"
    )
    google_calendar_frontend_return_url: str = "http://localhost:5173/google-calendar"
    google_calendar_token_encryption_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
