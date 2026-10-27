from http import HTTPStatus

from fastapi import APIRouter

from app.api.deps import DashboardServiceDep
from app.api.errors import error_responses
from app.schemas.widget import WidgetRead

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.post(
    "/reset",
    name="reset",
    summary="Reset the dashboard to its seeded state",
    status_code=HTTPStatus.OK,
    response_model=list[WidgetRead],
    responses=error_responses(HTTPStatus.SERVICE_UNAVAILABLE),
)
async def reset_dashboard(service: DashboardServiceDep) -> list[WidgetRead]:
    """Delete every widget and dataset, then import the provided seed files again."""
    return await service.reset()
