from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from environment variables."""

    # App
    app_name: str = "Novestia"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://novestia:novestia@localhost:5432/novestia"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # External APIs
    finnhub_api_key: str = ""
    gemini_api_key: str = ""

    # Clerk
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""

    # Observability
    sentry_dsn: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
