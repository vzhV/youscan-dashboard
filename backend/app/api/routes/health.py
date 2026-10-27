from http import HTTPStatus

from fastapi import APIRouter

from app.api.errors import error_responses
from app.schemas.health import HealthRead

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Check service health",
    status_code=HTTPStatus.OK,
    response_model=HealthRead,
    responses=error_responses(),
)
async def get_health() -> HealthRead:
    """Report that the API process is up and able to answer requests."""
    return HealthRead(status="ok")
