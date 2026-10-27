from http import HTTPStatus

from fastapi import APIRouter

from app.api.deps import SessionDep
from app.api.errors import error_responses
from app.schemas.health import HealthRead
from app.services import health_service

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Check service health",
    status_code=HTTPStatus.OK,
    response_model=HealthRead,
    responses=error_responses(HTTPStatus.SERVICE_UNAVAILABLE),
)
async def get_health(session: SessionDep) -> HealthRead:
    """Report that the API is up and the database answers a probe query."""
    return await health_service.check_health(session)
