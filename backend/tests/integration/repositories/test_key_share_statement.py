from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.repositories.dataset_repository import SqlDatasetRepository


async def test_get_for_widget_locks_the_row_with_for_key_share(
    db_session: AsyncSession, engine: AsyncEngine
) -> None:
    statements: list[str] = []

    def capture(_conn: object, _cursor: object, statement: str, *_rest: object) -> None:
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        await SqlDatasetRepository(db_session).get_for_widget(uuid4())
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)

    assert any(statement.endswith("FOR KEY SHARE") for statement in statements)
