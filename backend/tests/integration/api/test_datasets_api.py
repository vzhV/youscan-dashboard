from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DatasetOrigin
from app.repositories.dataset_repository import SqlDatasetRepository
from app.schemas.dataset import DatasetRead
from app.schemas.widget import WidgetRead
from tests.factories import make_dataset

DATASETS_URL = "/api/v1/datasets"
RESET_URL = "/api/v1/dashboard/reset"
WIDGETS_URL = "/api/v1/widgets"
EXPECTED_OPERATION_IDS = {
    "datasets-list",
    "datasets-add-to-dashboard",
    "datasets-delete",
    "dashboard-reset",
}


async def list_datasets(client: AsyncClient) -> list[DatasetRead]:
    response = await client.get(DATASETS_URL)
    assert response.status_code == 200
    return [DatasetRead.model_validate(item) for item in response.json()]


async def test_datasets_and_dashboard_operation_ids_are_stable(client: AsyncClient) -> None:
    schema = (await client.get("/api/v1/openapi.json")).json()

    operation_ids = {
        operation["operationId"]
        for path, item in schema["paths"].items()
        if path.startswith((DATASETS_URL, "/api/v1/dashboard"))
        for operation in item.values()
    }

    assert operation_ids == EXPECTED_OPERATION_IDS


async def test_get_datasets_returns_seed_datasets(client: AsyncClient) -> None:
    await client.post(RESET_URL)

    datasets = await list_datasets(client)

    assert [(item.name, item.origin, item.row_count, item.widget_count) for item in datasets] == [
        ("line chart data", DatasetOrigin.SEED, 212, 1),
        ("pie chart data", DatasetOrigin.SEED, 5, 1),
        ("stacked-bar", DatasetOrigin.SEED, 5, 1),
    ]


async def test_get_datasets_hides_generated_datasets(client: AsyncClient) -> None:
    await client.post(WIDGETS_URL, json={"type": "line"})

    assert await list_datasets(client) == []


async def test_post_dataset_widget_returns_201(client: AsyncClient) -> None:
    await client.post(RESET_URL)
    [first, *_] = await list_datasets(client)

    response = await client.post(f"{DATASETS_URL}/{first.id}/widgets")

    created = WidgetRead.model_validate(response.json())
    assert response.status_code == 201
    assert (created.type.value, created.title, created.position) == (first.chart_type.value, first.name, 3)
    assert (await list_datasets(client))[0].widget_count == 2


async def test_post_dataset_widget_for_generated_dataset_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    generated = await SqlDatasetRepository(db_session).add(make_dataset(origin=DatasetOrigin.GENERATED))

    response = await client.post(f"{DATASETS_URL}/{generated.id}/widgets")

    assert response.status_code == 404
    assert response.json()["error"]["details"] == {"dataset_id": str(generated.id)}


async def test_delete_dataset_returns_204_and_removes_widgets(client: AsyncClient) -> None:
    await client.post(RESET_URL)
    [first, *_] = await list_datasets(client)
    await client.post(f"{DATASETS_URL}/{first.id}/widgets")

    response = await client.delete(f"{DATASETS_URL}/{first.id}")

    assert response.status_code == 204
    assert len((await client.get(WIDGETS_URL)).json()) == 2
    assert len(await list_datasets(client)) == 2


async def test_delete_unknown_dataset_returns_404(client: AsyncClient) -> None:
    missing = uuid4()

    response = await client.delete(f"{DATASETS_URL}/{missing}")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "not_found",
        "message": "Dataset not found",
        "details": {"dataset_id": str(missing)},
    }


async def test_delete_generated_dataset_returns_404(client: AsyncClient, db_session: AsyncSession) -> None:
    generated = await SqlDatasetRepository(db_session).add(make_dataset(origin=DatasetOrigin.GENERATED))

    response = await client.delete(f"{DATASETS_URL}/{generated.id}")

    assert response.status_code == 404
    assert response.json()["error"]["details"] == {"dataset_id": str(generated.id)}
