from pathlib import Path

from alembic.config import Config

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def make_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    # Attributes bypass configparser, so a `%` in a password is never interpolated.
    config.attributes["database_url"] = database_url
    # Callers (the CLI, tests) own their logging; env.py's fileConfig would replace it.
    config.attributes["skip_logging_setup"] = True
    return config
