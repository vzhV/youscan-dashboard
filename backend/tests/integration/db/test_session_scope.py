from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.db import create_engine, create_session_factory, session_scope
from app.core.errors import DatabaseUnavailableError

INSERT_DATASET = text(
    "INSERT INTO datasets (id, name, origin, chart_type, row_count, data, display_data) "
    "VALUES (:id, 'scope', 'seed', 'line', 0, '{}', '{}')"
)
COUNT_DATASET = text("SELECT count(*) FROM datasets WHERE id = :id")
DELETE_DATASET = text("DELETE FROM datasets WHERE id = :id")


class BodyError(Exception):
    pass


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(engine)


@pytest.fixture
async def unreachable_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://x:x@127.0.0.1:1/x")
    unreachable_engine = create_engine(settings)
    yield create_session_factory(unreachable_engine)
    await unreachable_engine.dispose()


async def count_rows(engine: AsyncEngine, dataset_id: str) -> int:
    async with engine.connect() as connection:
        return int((await connection.execute(COUNT_DATASET, {"id": dataset_id})).scalar_one())


async def test_session_scope_commits_on_success(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
) -> None:
    dataset_id = str(uuid4())

    try:
        async with session_scope(factory) as session:
            await session.execute(INSERT_DATASET, {"id": dataset_id})
        visible_rows = await count_rows(engine, dataset_id)
    finally:
        async with engine.begin() as connection:
            await connection.execute(DELETE_DATASET, {"id": dataset_id})

    assert visible_rows == 1


async def test_session_scope_rolls_back_on_error(
    engine: AsyncEngine,
    factory: async_sessionmaker[AsyncSession],
) -> None:
    dataset_id = str(uuid4())

    async def insert_then_fail() -> None:
        async with session_scope(factory) as session:
            await session.execute(INSERT_DATASET, {"id": dataset_id})
            raise BodyError

    with pytest.raises(BodyError):
        await insert_then_fail()

    assert await count_rows(engine, dataset_id) == 0


async def test_session_scope_maps_unreachable_database_to_domain_error(
    unreachable_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(DatabaseUnavailableError, match="Database is unreachable"):
        async with session_scope(unreachable_factory) as session:
            await session.execute(text("SELECT 1"))


async def test_session_scope_propagates_non_database_errors_unchanged(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    async def fail_with_file_error() -> None:
        async with session_scope(factory):
            raise FileNotFoundError("missing.csv")

    with pytest.raises(FileNotFoundError):
        await fail_with_file_error()
