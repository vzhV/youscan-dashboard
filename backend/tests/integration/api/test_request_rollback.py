from fastapi import FastAPI
from httpx import AsyncClient

from app.api.deps import SessionDep
from app.core.errors import NotFoundError
from app.repositories.widget_repository import SqlWidgetRepository
from tests.factories import make_widget

FAILING_URL = "/api/v1/test-only/write-then-fail"


async def test_request_failing_after_a_write_is_rolled_back(app: FastAPI, client: AsyncClient) -> None:
    async def write_then_fail(session: SessionDep) -> None:
        await SqlWidgetRepository(session).add(make_widget(title="partial"))
        raise NotFoundError("simulated failure after a write")

    app.add_api_route(FAILING_URL, write_then_fail, methods=["POST"], tags=["test-only"])

    failed = await client.post(FAILING_URL)
    listed = await client.get("/api/v1/widgets")

    assert failed.status_code == 404
    assert listed.json() == []
