from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


async def test_health_reports_database_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_returns_503_when_database_unreachable() -> None:
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://x:x@127.0.0.1:1/x")
    app = create_app(settings)

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
