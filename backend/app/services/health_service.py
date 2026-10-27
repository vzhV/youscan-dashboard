from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import health_repository
from app.schemas.health import HealthRead


async def check_health(session: AsyncSession) -> HealthRead:
    """Probe the database.

    Uses the concrete `health_repository`: health has no aggregate or fake to swap, whereas real
    aggregates are reached through repository protocols.
    """
    await health_repository.ping(session)
    return HealthRead(status="ok", database="ok")
