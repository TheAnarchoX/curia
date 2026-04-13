"""Worker configuration loaded from environment variables."""

import uuid

from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    """Curia worker configuration."""

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    database_url: str = "postgresql+asyncpg://curia:curia@localhost:5432/curia"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "info"
    ibabs_base_url: str | None = None
    ibabs_municipality_slug: str | None = None
    ibabs_governing_body_id: uuid.UUID | None = None
    ibabs_max_pages: int = 100
    ibabs_rate_limit_rps: float = 2.0
    ibabs_timeout_seconds: float = 30.0
    ibabs_retry_max: int = 3

    model_config = {"env_file": ".env"}
