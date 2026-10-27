import logging

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.db import engine_options, rollback_quietly

DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 5
POOL_RECYCLE_SECONDS = 300


def make_settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, database_url="postgresql+psycopg://unused/unused", **overrides)  # type: ignore[arg-type]  # overrides are validated by pydantic


def test_engine_options_default_pool() -> None:
    options = engine_options(make_settings())

    assert options == {
        "pool_size": DEFAULT_POOL_SIZE,
        "max_overflow": DEFAULT_MAX_OVERFLOW,
        "pool_pre_ping": True,
        "pool_recycle": POOL_RECYCLE_SECONDS,
    }


def test_engine_options_disable_prepared_statements_when_flag_set() -> None:
    options = engine_options(make_settings(db_disable_prepared_statements=True))

    assert options["connect_args"] == {"prepare_threshold": None}


class BrokenRollbackSession(AsyncSession):
    async def rollback(self) -> None:
        raise ConnectionError("connection already lost")


async def test_rollback_quietly_logs_instead_of_raising_when_rollback_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = BrokenRollbackSession()

    with caplog.at_level(logging.WARNING, logger="app.core.db"):
        await rollback_quietly(session)

    assert "Rollback failed" in caplog.text
