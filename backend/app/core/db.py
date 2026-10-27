import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.errors import DatabaseUnavailableError

logger = logging.getLogger(__name__)

POOL_RECYCLE_SECONDS = 300
# Errors that mean "the database cannot be reached"; anything else is a bug and must propagate unchanged.
UNREACHABLE_ERRORS = (OperationalError, ConnectionError)


def engine_options(settings: Settings) -> dict[str, object]:
    options: dict[str, object] = {
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_pre_ping": True,
        "pool_recycle": POOL_RECYCLE_SECONDS,
    }
    if settings.db_disable_prepared_statements:
        # Supabase's transaction pooler cannot serve server-side prepared statements.
        options["connect_args"] = {"prepare_threshold": None}
    return options


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, **engine_options(settings))


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def rollback_quietly(session: AsyncSession) -> None:
    # A dead connection also fails the rollback; that must not hide the error being handled.
    try:
        await session.rollback()
    except Exception:
        logger.warning("Rollback failed while handling an earlier error", exc_info=True)


@asynccontextmanager
async def session_scope(factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """One transaction: commit on success, roll back on error, always close.

    This is the only place that maps database outages to `DatabaseUnavailableError`.
    """
    session = factory()
    try:
        yield session
        await session.commit()
    except UNREACHABLE_ERRORS as error:
        await rollback_quietly(session)
        raise DatabaseUnavailableError("Database is unreachable") from error
    except BaseException:
        await rollback_quietly(session)
        raise
    finally:
        await session.close()
