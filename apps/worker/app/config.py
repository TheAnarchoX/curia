"""Worker configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    """Curia worker configuration."""

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    database_url: str = "postgresql+asyncpg://curia:curia@localhost:5432/curia"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "info"

    model_config = {"env_file": ".env"}
