"""Application settings loaded from environment variables."""

import json
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class Settings(BaseSettings):
    """Curia API configuration."""

    database_url: str = "postgresql+asyncpg://curia:curia@localhost:5432/curia"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    debug: bool = False

    model_config = {"env_file": ".env"}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        """Allow CORS origins to be provided as JSON or comma-separated text."""
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value
