from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DatasetOrigin
from app.repositories.dataset_repository import SqlDatasetRepository
from app.repositories.widget_repository import SqlWidgetRepository
from app.schemas.widget import WidgetRead
from tests.factories import OLD_TIMESTAMP, make_chart_widget, make_dataset

WIDGETS_URL = "/api/v1/widgets"
EXPECTED_OPERATION_IDS = {
    "widgets-list",
    "widgets-create",
    "widgets-update",
    "widgets-delete",
    "widgets-get-data",
}


async def create_widget(client: AsyncClient, **payload: object) -> WidgetRead:
    response = await client.post(WIDGETS_URL, json=payload)
    assert response.status_code == 201
    return WidgetRead.model_validate(response.json())


async def test_widget_operation_ids_are_stable(client: AsyncClient) -> None:
    schema = (await client.get("/api/v1/openapi.json")).json()

    operation_ids = {
        operation["operationId"]
        for path, item in schema["paths"].items()
        if path.startswith(WIDGETS_URL)
        for operation in item.values()
    }

    assert operation_ids == EXPECTED_OPERATION_IDS


async def test_list_widgets_returns_metadata_without_chart_data(client: AsyncClient) -> None:
    await create_widget(client, type="line")
    await create_widget(client, type="text")

    items = (await client.get(WIDGETS_URL)).json()

    assert [item["type"] for item in items] == ["line", "text"]
    for item in items:
        assert "data" not in item
        assert "categories" not in item


async def test_create_widget_returns_201(client: AsyncClient) -> None:
    response = await client.post(WIDGETS_URL, json={"type": "bar"})

    assert response.status_code == 201
    assert response.json()["title"] == "Bar chart 1"


async def test_create_chart_widget_returns_generated_source(client: AsyncClient) -> None:
    created = await create_widget(client, type="pie")

    assert created.source is not None
    assert created.source.origin == DatasetOrigin.GENERATED


async def test_create_chart_widget_default_titles_are_numbered_per_type(client: AsyncClient) -> None:
    titles = [(await create_widget(client, type=kind)).title for kind in ("line", "bar", "line")]

    assert titles == ["Line chart 1", "Bar chart 1", "Line chart 2"]


async def test_patch_text_content_persists(client: AsyncClient) -> None:
    created = await create_widget(client, type="text")

    patched = await client.patch(f"{WIDGETS_URL}/{created.id}", json={"text_content": "Hello"})
    listed = (await client.get(WIDGETS_URL)).json()

    assert patched.status_code == 200
    assert listed[0]["text_content"] == "Hello"


async def test_patch_returns_new_updated_at(client: AsyncClient, db_session: AsyncSession) -> None:
    created = await create_widget(client, type="text")
    stored = await SqlWidgetRepository(db_session).get(created.id)
    assert stored is not None
    stored.updated_at = OLD_TIMESTAMP
    await db_session.flush()

    patched = await client.patch(f"{WIDGETS_URL}/{created.id}", json={"title": "New"})

    assert datetime.fromisoformat(patched.json()["updated_at"]) > OLD_TIMESTAMP


async def test_delete_returns_204_then_404(client: AsyncClient) -> None:
    created = await create_widget(client, type="text")
    url = f"{WIDGETS_URL}/{created.id}"

    first = await client.delete(url)
    second = await client.delete(url)

    assert first.status_code == 204
    assert second.status_code == 404


async def test_delete_chart_widget_removes_its_generated_dataset(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    created = await create_widget(client, type="line")
    assert created.source is not None

    await client.delete(f"{WIDGETS_URL}/{created.id}")

    assert await SqlDatasetRepository(db_session).get(created.source.dataset_id) is None


async def test_delete_widget_keeps_uploaded_dataset(client: AsyncClient, db_session: AsyncSession) -> None:
    datasets = SqlDatasetRepository(db_session)
    dataset = await datasets.add(make_dataset(origin=DatasetOrigin.UPLOAD))
    widget = await SqlWidgetRepository(db_session).add(make_chart_widget(dataset.id))

    response = await client.delete(f"{WIDGETS_URL}/{widget.id}")

    assert response.status_code == 204
    assert await datasets.get(dataset.id) is not None


async def test_widget_data_returns_chart_data(client: AsyncClient) -> None:
    created = await create_widget(client, type="bar")

    body = (await client.get(f"{WIDGETS_URL}/{created.id}/data")).json()

    assert body["categories"]
    assert body["series"]


async def test_widget_data_for_text_widget_returns_409(client: AsyncClient) -> None:
    created = await create_widget(client, type="text")

    response = await client.get(f"{WIDGETS_URL}/{created.id}/data")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "widget_has_no_data"


@pytest.mark.parametrize(
    ("method", "path_suffix", "body"),
    [("PATCH", "", {"title": "x"}), ("DELETE", "", None), ("GET", "/data", None)],
    ids=["update", "delete", "get-data"],
)
async def test_unknown_widget_id_returns_404(
    client: AsyncClient, method: str, path_suffix: str, body: dict[str, str] | None
) -> None:
    widget_id = uuid4()

    response = await client.request(method, f"{WIDGETS_URL}/{widget_id}{path_suffix}", json=body)

    error = response.json()["error"]
    assert response.status_code == 404
    assert error["code"] == "not_found"
    assert error["details"] == {"widget_id": str(widget_id)}


async def test_text_content_on_chart_widget_returns_422(client: AsyncClient) -> None:
    created = await create_widget(client, type="line")

    response = await client.patch(f"{WIDGETS_URL}/{created.id}", json={"text_content": "x"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
