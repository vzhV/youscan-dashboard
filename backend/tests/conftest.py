import os

# app.main builds the app at import time and Settings requires a URL; tests never connect with this one.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://unused/unused")

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    # _env_file=None keeps a developer's backend/.env out of the tests.
    return Settings(_env_file=None, database_url="postgresql+psycopg://unused/unused", environment="test")


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http_client:
        yield http_client
