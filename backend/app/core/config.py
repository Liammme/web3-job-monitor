from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Web3 Job Monitor"
    env: str = "dev"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/web3_jobs"

    auth_username: str = "admin"
    auth_password: str = "change-me"
    jwt_secret: str = "change-me-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    discord_webhook_url: str = ""


settings = Settings()
