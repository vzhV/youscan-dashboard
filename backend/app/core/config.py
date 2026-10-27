from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BeforeValidator, NonNegativeInt, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict

BYTES_PER_MEGABYTE = 1024 * 1024
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, case_sensitive=False, extra="ignore", env_ignore_empty=True
    )

    environment: Literal["local", "test", "production"] = "local"
    database_url: str
    migrations_database_url: str | None = None
    test_database_url: str | None = None
    db_pool_size: PositiveInt = 5
    db_max_overflow: NonNegativeInt = 5
    db_disable_prepared_statements: bool = False
    max_upload_mb: PositiveInt = 4
    log_level: Annotated[LogLevel, BeforeValidator(str.upper)] = "INFO"

    @property
    def effective_migrations_url(self) -> str:
        return self.migrations_database_url or self.database_url

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * BYTES_PER_MEGABYTE


@lru_cache
def get_settings() -> Settings:
    return Settings()
