from uuid import UUID

from sqlalchemy import Select, delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import WidgetType
from app.models import Widget

# Arbitrary application-wide key naming the board lock; any constant unique among our advisory locks works.
BOARD_LOCK_KEY = 7_201_027


def _widgets_with_dataset() -> Select[Widget]:
    # Dataset payload columns stay deferred, so only metadata is loaded.
    return select(Widget).options(selectinload(Widget.dataset))


class SqlWidgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_ordered(self) -> list[Widget]:
        statement = _widgets_with_dataset().order_by(Widget.position, Widget.created_at, Widget.id)
        return list((await self._session.scalars(statement)).all())

    async def get(self, widget_id: UUID) -> Widget | None:
        # A select rather than session.get: the DB cascade deletes rows behind the identity map's back.
        statement = _widgets_with_dataset().where(Widget.id == widget_id)
        return await self._session.scalar(statement)

    async def add(self, widget: Widget) -> Widget:
        self._session.add(widget)
        await self._session.flush()
        # Re-select so the dataset relationship is loaded the same way list_ordered and get load it.
        statement = _widgets_with_dataset().where(Widget.id == widget.id)
        return (await self._session.scalars(statement)).one()

    async def save(self, widget: Widget) -> Widget:
        # Flushing here lets onupdate refresh updated_at before the caller builds its response.
        await self._session.flush()
        return widget

    async def delete(self, widget: Widget) -> None:
        await self._session.delete(widget)
        await self._session.flush()

    async def next_position(self) -> int:
        highest = await self._session.scalar(select(func.max(Widget.position)))
        return 0 if highest is None else highest + 1

    async def count_by_type(self, widget_type: WidgetType) -> int:
        statement = select(func.count()).select_from(Widget).where(Widget.type == widget_type)
        return await self._session.scalar(statement) or 0

    async def delete_all(self) -> None:
        await self._session.execute(delete(Widget))
        self._session.expunge_all()

    async def lock_board(self) -> None:
        # Serializes board-replacing requests: without it, concurrent resets each delete, then all insert.
        # A transaction-level lock is released on commit or rollback, so it works behind a transaction pooler.
        await self._session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": BOARD_LOCK_KEY})
