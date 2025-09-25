"""Application settings and configuration utilities."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Declarative settings loaded from environment variables/.env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = Field(default="Batumi Lunch API")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    api_v1_prefix: str = Field(default="/api/v1")

    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="batumi_lunch")
    postgres_user: str = Field(default="batumi")
    postgres_password: str = Field(default="batumi_pass")

    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    s3_endpoint: str = Field(default="http://localhost:9000")
    s3_access_key: str = Field(default="minio")
    s3_secret_key: str = Field(default="minio_secret")
    s3_bucket: str = Field(default="batumi-lunch")
    s3_region: str = Field(default="us-east-1")
    s3_secure: bool = Field(default=False)

    jwt_secret: str = Field(default="change-me")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_ttl: int = Field(default=900)  # 15 minutes
    jwt_refresh_ttl: int = Field(default=60 * 60 * 24 * 14)  # 14 days
    password_pepper: str = Field(default="pepper")

    timezone: str = Field(default="Asia/Tbilisi")
    order_cutoff_hour: int = Field(default=10)
    price_lari: int = Field(default=15)

    admin_telegram_ids: list[int] = Field(default_factory=list)
    default_admin_email: str | None = None

    frontend_url: str = Field(default="http://localhost:3000")
    backend_url: str = Field(default="http://localhost:8000")

    class Config:
        frozen = True

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: Any) -> list[int]:
        if value in (None, "", []):
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        if isinstance(value, str):
            parts = [p.strip() for p in value.split(",") if p.strip()]
            return [int(p) for p in parts]
        raise ValueError("Unsupported value for admin telegram ids")

    @property
    def database_url_async(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_dsn(self) -> str:
        return str(self.redis_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
