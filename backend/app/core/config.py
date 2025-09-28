from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(PROJECT_ROOT / ".env"),
            str(PROJECT_ROOT / ".env.local"),
            str(PROJECT_ROOT / ".env.sample"),
        ),
        env_prefix="BATUMI_LUNCH_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Batumi Lunch API"
    environment: str = Field(default="local", description="Deployment environment name")
    debug: bool = True

    database_url: PostgresDsn | None = None
    redis_url: str | None = "redis://localhost:6379/0"

    s3_endpoint_url: AnyHttpUrl | None = None
    s3_bucket: str = "batumi-lunch-media"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_minutes: int = 30
    jwt_refresh_token_ttl_minutes: int = 7 * 24 * 60

    order_price_lari: int = Field(default=15)
    order_daily_limit: int = Field(default=4)
    order_rate_limit_window_seconds: int = Field(default=10)
    orders_rate_limit_redis_key_prefix: str = Field(default="rate:orders")
    broadcasts_rate_limit_key_prefix: str = Field(default="rate:broadcasts")

    admin_email: str | None = None
    admin_telegram_id: int | None = None

    cors_allow_origins: list[AnyHttpUrl] | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


__all__ = ["settings", "get_settings", "Settings"]
