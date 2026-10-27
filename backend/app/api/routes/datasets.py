from collections.abc import Mapping
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Response

from app.api.deps import DatasetServiceDep
from app.api.errors import error_responses, invalid_path_parameter_example
from app.schemas.common import ErrorBody
from app.schemas.dataset import DatasetRead
from app.schemas.widget import WidgetRead

DATASET_EXAMPLES: Mapping[int, ErrorBody] = {
    HTTPStatus.NOT_FOUND: ErrorBody(
        code="not_found",
        message="Dataset not found",
        details={"dataset_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"},
    ),
    HTTPStatus.UNPROCESSABLE_ENTITY: invalid_path_parameter_example("dataset_id"),
}

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get(
    "",
    name="list",
    summary="List datasets",
    status_code=HTTPStatus.OK,
    response_model=list[DatasetRead],
    responses=error_responses(HTTPStatus.SERVICE_UNAVAILABLE),
)
async def list_datasets(service: DatasetServiceDep) -> list[DatasetRead]:
    """Return the seeded and uploaded datasets with the number of widgets showing each.

    Datasets generated for random charts are never listed.
    """
    return await service.list_datasets()


@router.post(
    "/{dataset_id}/widgets",
    name="add_to_dashboard",
    summary="Add a dataset to the dashboard",
    status_code=HTTPStatus.CREATED,
    response_model=WidgetRead,
    responses=error_responses(
        HTTPStatus.NOT_FOUND,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        examples=DATASET_EXAMPLES,
    ),
)
async def add_dataset_to_dashboard(dataset_id: UUID, service: DatasetServiceDep) -> WidgetRead:
    """Append a widget that shows the dataset, titled with the dataset name and typed by its chart type."""
    return await service.add_to_dashboard(dataset_id)


@router.delete(
    "/{dataset_id}",
    name="delete",
    summary="Delete a dataset",
    status_code=HTTPStatus.NO_CONTENT,
    response_class=Response,
    responses=error_responses(
        HTTPStatus.NOT_FOUND,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        examples=DATASET_EXAMPLES,
    ),
)
async def delete_dataset(dataset_id: UUID, service: DatasetServiceDep) -> Response:
    """Remove a dataset together with every widget that shows it."""
    await service.delete_dataset(dataset_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)
