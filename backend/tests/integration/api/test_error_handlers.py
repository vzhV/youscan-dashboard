import logging
from collections.abc import AsyncIterator

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.config import Settings
from app.core.errors import DomainError, NotFoundError, SeedDataError
from app.main import create_app


class UnmappedError(DomainError):
    code = "unmapped"


class Payload(BaseModel):
    name: str


@pytest.fixture
async def probe_client(settings: Settings) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    router = APIRouter(prefix="/__test", tags=["test"])

    @router.get("/missing")
    async def missing() -> None:
        raise NotFoundError("Widget not found")

    @router.get("/corrupt-seed")
    async def corrupt_seed() -> None:
        raise SeedDataError("Seed file 'x.csv' could not be imported: bad")

    @router.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret")

    @router.get("/unmapped")
    async def unmapped() -> None:
        raise UnmappedError("not in the catalog")

    @router.post("/echo")
    async def echo(payload: Payload) -> Payload:
        return payload

    app.include_router(router)
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_domain_error_maps_to_status_and_error_body(probe_client: AsyncClient) -> None:
    response = await probe_client.get("/__test/missing")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Widget not found", "details": None}}


async def test_request_validation_error_uses_error_body_with_field_details(probe_client: AsyncClient) -> None:
    response = await probe_client.post("/__test/echo", json={})

    body = response.json()["error"]
    assert response.status_code == 422
    assert body["code"] == "validation_error"
    assert body["details"]["fields"][0]["loc"][-1] == "name"


async def test_unhandled_error_returns_500_without_internals(probe_client: AsyncClient) -> None:
    response = await probe_client.get("/__test/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.json()["error"]["message"] == "Internal server error"
    assert "secret" not in response.text


async def test_unknown_route_returns_404_error_body(probe_client: AsyncClient) -> None:
    response = await probe_client.get("/api/v1/nope")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_wrong_method_returns_405_error_body(probe_client: AsyncClient) -> None:
    response = await probe_client.post("/api/v1/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


async def test_method_not_allowed_response_keeps_the_allow_header(probe_client: AsyncClient) -> None:
    response = await probe_client.post("/api/v1/health")

    assert "GET" in response.headers["allow"]


async def test_unmapped_domain_error_falls_through_to_internal_error(probe_client: AsyncClient) -> None:
    response = await probe_client.get("/__test/unmapped")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


async def test_server_side_domain_error_is_logged_at_error_level(
    probe_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    response = await probe_client.get("/__test/corrupt-seed")

    assert response.status_code == 500
    [record] = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert "seed_data_invalid" in record.getMessage()
    assert record.exc_info is not None


async def test_client_side_domain_error_is_not_logged_at_error_level(
    probe_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    await probe_client.get("/__test/missing")

    assert not [record for record in caplog.records if record.levelno >= logging.ERROR]


async def test_error_without_details_still_returns_a_null_details_field(client: AsyncClient) -> None:
    text_widget = (await client.post("/api/v1/widgets", json={"type": "text"})).json()

    response = await client.get(f"/api/v1/widgets/{text_widget['id']}/data")

    assert response.status_code == 409
    assert response.json()["error"]["details"] is None
    assert "details" in response.json()["error"]
