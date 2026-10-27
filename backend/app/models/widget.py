import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import WidgetType
from app.models.base import NAME_LENGTH, Base, list_enum_values, utc_now
from app.models.dataset import Dataset


class Widget(Base):
    __tablename__ = "widgets"
    __table_args__ = (
        CheckConstraint("(type = 'text') = (dataset_id IS NULL)", name="text_iff_no_dataset"),
        CheckConstraint("type = 'text' OR text_content IS NULL", name="text_content_only_for_text"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[WidgetType] = mapped_column(
        Enum(WidgetType, name="widget_type", values_callable=list_enum_values)
    )
    title: Mapped[str] = mapped_column(String(NAME_LENGTH))
    position: Mapped[int] = mapped_column(index=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    text_content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utc_now, onupdate=utc_now
    )

    # lazy="raise" forces the repository to join explicitly instead of triggering hidden IO.
    dataset: Mapped[Dataset | None] = relationship(lazy="raise")
