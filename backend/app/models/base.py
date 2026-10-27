from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

NAME_LENGTH = 100
FILE_FIELD_LENGTH = 255


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def list_enum_values(enum_class: type[StrEnum]) -> list[str]:
    # Stores the lowercase values rather than the member names in the Postgres enum.
    return [member.value for member in enum_class]


def utc_now() -> datetime:
    return datetime.now(UTC)
