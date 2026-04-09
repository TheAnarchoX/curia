"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Curia API configuration."""

    database_url: str = "postgresql+asyncpg://curia:curia@localhost:5432/curia"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"
    cors_origins: list[str] = ["http://localhost:3000"]
    debug: bool = False

    model_config = {"env_file": ".env", "env_prefix": "CURIA_"}
