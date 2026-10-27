import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ChartType, DatasetOrigin
from app.models.base import FILE_FIELD_LENGTH, NAME_LENGTH, Base, list_enum_values, utc_now


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(NAME_LENGTH))
    origin: Mapped[DatasetOrigin] = mapped_column(
        Enum(DatasetOrigin, name="dataset_origin", values_callable=list_enum_values)
    )
    chart_type: Mapped[ChartType] = mapped_column(
        Enum(ChartType, name="chart_type", values_callable=list_enum_values)
    )
    source_filename: Mapped[str | None] = mapped_column(String(FILE_FIELD_LENGTH))
    source_sheet: Mapped[str | None] = mapped_column(String(FILE_FIELD_LENGTH))
    row_count: Mapped[int]
    # Deferred and raising so a list query can never drag the full payload along by accident.
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, deferred=True, deferred_raiseload=True)
    display_data: Mapped[dict[str, Any]] = mapped_column(JSONB, deferred=True, deferred_raiseload=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utc_now
    )
