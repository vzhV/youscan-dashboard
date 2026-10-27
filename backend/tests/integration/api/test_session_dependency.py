from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


class FailingCommitSession(AsyncSession):
    async def commit(self) -> None:
        raise OperationalError("COMMIT", None, ConnectionError("connection lost"))


async def test_failed_commit_returns_503_instead_of_a_sent_200(app: FastAPI, engine: AsyncEngine) -> None:
    app.state.session_factory = async_sessionmaker[FailingCommitSession](engine, class_=FailingCommitSession)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
