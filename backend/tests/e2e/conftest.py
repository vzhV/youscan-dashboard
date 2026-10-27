"""Black-box CLI tests against the migrated test database.

The dev database is never touched: DATABASE_URL is pointed at TEST_DATABASE_URL and verified before use.
"""

from collections.abc import Callable, Iterator

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from typer.testing import CliRunner

from app.core.config import Settings, get_settings
from app.core.migrations import make_alembic_config

TRUNCATE_BOARD = "TRUNCATE TABLE widgets, datasets CASCADE"
SELECT_TITLES = "SELECT title FROM widgets ORDER BY position"
COUNT_DATASETS = "SELECT count(*) FROM datasets"


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = Settings().test_database_url
    if not url:
        pytest.fail("Set TEST_DATABASE_URL (see backend/.env.example)")
    # Tests truncate the board tables; pointing them at the application database would wipe real data.
    if url == Settings().database_url:
        pytest.fail("TEST_DATABASE_URL equals DATABASE_URL; refusing to truncate the application database")
    return url


@pytest.fixture(scope="session", autouse=True)
def migrated_test_database(test_database_url: str) -> None:
    command.upgrade(make_alembic_config(test_database_url), "head")


def _truncate_board(url: str) -> None:
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text(TRUNCATE_BOARD))
    engine.dispose()


@pytest.fixture(autouse=True)
def isolated_board(test_database_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("DATABASE_URL", test_database_url)
    # `migrate` prefers MIGRATIONS_DATABASE_URL, which a developer's .env may point at a real database.
    monkeypatch.setenv("MIGRATIONS_DATABASE_URL", test_database_url)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.database_url == test_database_url, "CLI would not use the test database"
    assert settings.effective_migrations_url == test_database_url, "migrate would not use the test database"
    _truncate_board(test_database_url)
    yield
    # Integration tests share this database and must never see CLI residue.
    _truncate_board(test_database_url)
    get_settings.cache_clear()


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def board_titles(test_database_url: str) -> Callable[[], list[str]]:
    def fetch() -> list[str]:
        engine = create_engine(test_database_url)
        with engine.connect() as connection:
            titles = [row[0] for row in connection.execute(text(SELECT_TITLES))]
        engine.dispose()
        return titles

    return fetch


@pytest.fixture
def dataset_count(test_database_url: str) -> Callable[[], int]:
    def fetch() -> int:
        engine = create_engine(test_database_url)
        with engine.connect() as connection:
            count = int(connection.execute(text(COUNT_DATASETS)).scalar_one())
        engine.dispose()
        return count

    return fetch
