from collections.abc import Mapping
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Response

from app.api.deps import WidgetServiceDep
from app.api.errors import error_responses, invalid_path_parameter_example
from app.schemas.chart import ChartData
from app.schemas.common import ErrorBody
from app.schemas.widget import WidgetCreate, WidgetRead, WidgetUpdate

# PATCH also validates a body; its 422 example shows the path case, and a body 422 has the same shape with a
# "body" loc.
INVALID_WIDGET_ID: Mapping[int, ErrorBody] = {
    HTTPStatus.UNPROCESSABLE_ENTITY: invalid_path_parameter_example("widget_id")
}

router = APIRouter(prefix="/widgets", tags=["widgets"])


@router.get(
    "",
    name="list",
    summary="List widgets",
    status_code=HTTPStatus.OK,
    response_model=list[WidgetRead],
    responses=error_responses(HTTPStatus.SERVICE_UNAVAILABLE),
)
async def list_widgets(service: WidgetServiceDep) -> list[WidgetRead]:
    """Return every widget in board order, without chart data."""
    return await service.list_widgets()


@router.post(
    "",
    name="create",
    summary="Create a widget",
    status_code=HTTPStatus.CREATED,
    response_model=WidgetRead,
    responses=error_responses(HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.SERVICE_UNAVAILABLE),
)
async def create_widget(payload: WidgetCreate, service: WidgetServiceDep) -> WidgetRead:
    """Append a widget to the board. Chart widgets get randomly generated data."""
    return await service.create_widget(payload)


@router.patch(
    "/{widget_id}",
    name="update",
    summary="Rename a widget or edit its text",
    status_code=HTTPStatus.OK,
    response_model=WidgetRead,
    responses=error_responses(
        HTTPStatus.NOT_FOUND,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        examples=INVALID_WIDGET_ID,
    ),
)
async def update_widget(widget_id: UUID, payload: WidgetUpdate, service: WidgetServiceDep) -> WidgetRead:
    """Change the title, the text content or both. Text content is accepted only by text widgets."""
    return await service.update_widget(widget_id, payload)


@router.delete(
    "/{widget_id}",
    name="delete",
    summary="Delete a widget",
    status_code=HTTPStatus.NO_CONTENT,
    response_class=Response,
    responses=error_responses(
        HTTPStatus.NOT_FOUND,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        examples=INVALID_WIDGET_ID,
    ),
)
async def delete_widget(widget_id: UUID, service: WidgetServiceDep) -> Response:
    """Remove a widget together with its randomly generated dataset, if it has one."""
    await service.delete_widget(widget_id)
    return Response(status_code=HTTPStatus.NO_CONTENT)


@router.get(
    "/{widget_id}/data",
    name="get_data",
    summary="Get a widget's chart data",
    status_code=HTTPStatus.OK,
    response_model=ChartData,
    responses=error_responses(
        HTTPStatus.NOT_FOUND,
        HTTPStatus.CONFLICT,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.SERVICE_UNAVAILABLE,
        examples=INVALID_WIDGET_ID,
    ),
)
async def get_widget_data(widget_id: UUID, service: WidgetServiceDep) -> ChartData:
    """Return the chart data, thinned to at most 1,000 categories. Text widgets answer 409."""
    return await service.get_widget_data(widget_id)
