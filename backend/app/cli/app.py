import typer

from app.cli import data_commands, ops_commands
from app.core.config import get_settings
from app.core.logging import configure_logging

cli = typer.Typer(no_args_is_help=True, help="Dashboard data and maintenance commands.")
cli.add_typer(data_commands.commands)
cli.add_typer(ops_commands.commands)


@cli.callback()
def configure() -> None:
    # Explicit rather than an import side effect; `--help` exits before this, so bad settings cannot block it.
    configure_logging(get_settings().log_level)
