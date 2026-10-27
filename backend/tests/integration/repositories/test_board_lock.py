from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.repositories.widget_repository import BOARD_LOCK_KEY, SqlWidgetRepository

TRY_LOCK = text("SELECT pg_try_advisory_xact_lock(:key)")


async def test_lock_board_blocks_other_connections_until_the_transaction_ends(
    db_session: AsyncSession, engine: AsyncEngine
) -> None:
    await SqlWidgetRepository(db_session).lock_board()

    async with engine.connect() as other:
        # Held because db_session's outer transaction is still open.
        assert await other.scalar(TRY_LOCK, {"key": BOARD_LOCK_KEY}) is False
        await other.rollback()
        await db_session.rollback()
        assert await other.scalar(TRY_LOCK, {"key": BOARD_LOCK_KEY}) is True
        await other.rollback()
