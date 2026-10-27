from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models  # noqa: F401  # registers every model on Base.metadata
from app.core.config import get_settings
from app.models.base import Base

config = context.config
# The CLI and the tests opt out (skip_logging_setup): fileConfig would replace their own logging setup.
if config.config_file_name is not None and not config.attributes.get("skip_logging_setup"):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def resolve_database_url() -> str:
    # Attributes instead of `sqlalchemy.url`: configparser would interpolate a `%` in a password.
    url: str | None = config.attributes.get("database_url")
    return url or get_settings().effective_migrations_url


def run_migrations_offline() -> None:
    context.configure(url=resolve_database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(resolve_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
