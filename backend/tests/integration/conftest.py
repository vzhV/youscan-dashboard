from collections.abc import AsyncIterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.api.deps import get_session
from app.core.config import Settings
from app.core.db import create_engine
from app.core.migrations import make_alembic_config


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = Settings().test_database_url
    if not url:
        pytest.fail("Set TEST_DATABASE_URL (see backend/.env.example)")
    return url


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    return make_alembic_config(test_database_url)


@pytest.fixture(scope="session")
def migrated_database(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session")
async def engine(test_database_url: str, migrated_database: None) -> AsyncIterator[AsyncEngine]:
    test_engine = create_engine(Settings(_env_file=None, database_url=test_database_url))
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    # The outer transaction is never committed, so each test starts from the migrated, empty schema.
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        yield session
        await session.close()
        await transaction.rollback()


@pytest.fixture
async def client(app: FastAPI, db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_session() -> AsyncIterator[AsyncSession]:
        # A failed request rolls back its partial writes, as session_scope does in production.
        async with db_session.begin_nested():
            yield db_session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
