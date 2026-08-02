"""FastAPI application config loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:sourceos@localhost:5432/sourceos"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: str = "./data"
    youtube_api_key: str = ""
    sentry_dsn: str = ""
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    web_username: str = "admin"
    web_password: str = "sourceos"
    pi_provider: str = ""
    pi_model: str = ""
    pi_runtime_command: str = "node agent-runtime/dist/main.js"
    pi_runtime_timeout_seconds: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
