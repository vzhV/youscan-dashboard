import pytest
from pydantic import ValidationError

from app.core.config import Settings

DATABASE_URL = "postgresql+psycopg://user:pass@localhost/db"


def test_settings_without_database_url_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_effective_migrations_url_defaults_to_database_url() -> None:
    assert Settings(_env_file=None, database_url=DATABASE_URL).effective_migrations_url == DATABASE_URL


def test_effective_migrations_url_prefers_explicit_value() -> None:
    settings = Settings(
        _env_file=None, database_url=DATABASE_URL, migrations_database_url="postgresql+psycopg://m/m"
    )

    assert settings.effective_migrations_url == "postgresql+psycopg://m/m"


def test_max_upload_bytes_converts_megabytes() -> None:
    assert (
        Settings(_env_file=None, database_url=DATABASE_URL, max_upload_mb=4).max_upload_bytes
        == 4 * 1024 * 1024
    )


@pytest.mark.parametrize("field", ["log_level", "db_pool_size", "db_max_overflow"])
def test_invalid_pool_or_log_values_raise_validation_error_naming_the_field(field: str) -> None:
    invalid = {"log_level": "LOUD", "db_pool_size": 0, "db_max_overflow": -1}

    with pytest.raises(ValidationError, match=field):
        Settings.model_validate({"database_url": DATABASE_URL, field: invalid[field]})


def test_log_level_is_case_insensitive() -> None:
    assert Settings(_env_file=None, database_url=DATABASE_URL, log_level="debug").log_level == "DEBUG"


def test_empty_environment_value_is_treated_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIGRATIONS_DATABASE_URL", "")

    settings = Settings(_env_file=None, database_url=DATABASE_URL)

    assert settings.migrations_database_url is None
