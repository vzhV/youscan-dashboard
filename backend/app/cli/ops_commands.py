import typer
from alembic import command
from sqlalchemy.exc import OperationalError

from app.cli.runtime import fail_with_message
from app.core.config import get_settings
from app.core.errors import DatabaseUnavailableError
from app.core.migrations import make_alembic_config

commands = typer.Typer()


@commands.command("migrate")
@fail_with_message
def migrate() -> None:
    """Apply database migrations (`alembic upgrade head`)."""
    config = make_alembic_config(get_settings().effective_migrations_url)
    try:
        command.upgrade(config, "head")
    except (OperationalError, ConnectionError) as error:
        raise DatabaseUnavailableError("Database is unreachable") from error
    typer.echo("Database is up to date")
