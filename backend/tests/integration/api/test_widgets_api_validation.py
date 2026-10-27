import pytest
from httpx import AsyncClient

from app.schemas.common import TEXT_MAX_LENGTH, TITLE_MAX_LENGTH

WIDGETS_URL = "/api/v1/widgets"
SOME_ID = "00000000-0000-4000-8000-000000000000"


async def assert_validation_error(client: AsyncClient, method: str, url: str, body: object) -> None:
    response = await client.request(method, url, json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_create_widget_with_unknown_type_returns_422(client: AsyncClient) -> None:
    await assert_validation_error(client, "POST", WIDGETS_URL, {"type": "radar"})


@pytest.mark.parametrize(
    "body",
    [
        {"title": "   "},
        {"title": "x" * (TITLE_MAX_LENGTH + 1)},
        {"text_content": "x" * (TEXT_MAX_LENGTH + 1)},
        {},
    ],
    ids=["whitespace-title", "long-title", "long-text", "empty-body"],
)
async def test_patch_with_invalid_body_returns_422(client: AsyncClient, body: dict[str, str]) -> None:
    await assert_validation_error(client, "PATCH", f"{WIDGETS_URL}/{SOME_ID}", body)


@pytest.mark.parametrize(
    ("method", "path_suffix", "body"),
    [("PATCH", "", {"title": "x"}), ("DELETE", "", None), ("GET", "/data", None)],
    ids=["update", "delete", "get-data"],
)
async def test_malformed_widget_id_returns_422(
    client: AsyncClient, method: str, path_suffix: str, body: dict[str, str] | None
) -> None:
    await assert_validation_error(client, method, f"{WIDGETS_URL}/not-a-uuid{path_suffix}", body)


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        ("POST", WIDGETS_URL, {"type": "bar", "bogus": 1}),
        ("PATCH", f"{WIDGETS_URL}/{SOME_ID}", {"title": "ok", "bogus": 1}),
    ],
    ids=["create", "update"],
)
async def test_unknown_request_field_returns_422(
    client: AsyncClient, method: str, url: str, body: dict[str, object]
) -> None:
    response = await client.request(method, url, json=body)

    error = response.json()["error"]
    assert response.status_code == 422
    assert error["code"] == "validation_error"
    assert error["details"]["fields"][0]["loc"][-1] == "bogus"
