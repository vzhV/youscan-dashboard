import functools
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import typer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory, session_scope
from app.core.errors import DomainError

FAILURE_EXIT_CODE = 1


@asynccontextmanager
async def open_session() -> AsyncIterator[AsyncSession]:
    """One transaction on a private engine, mirroring the per-request scope the API uses."""
    engine = create_engine(get_settings())
    try:
        async with session_scope(create_session_factory(engine)) as session:
            yield session
    finally:
        await engine.dispose()


def fail_with_message(command: Callable[..., None]) -> Callable[..., None]:
    """Turn an expected failure into one `Error:` line and exit code 1 instead of a traceback."""

    @functools.wraps(command)
    def wrapper(*args: object, **kwargs: object) -> None:
        try:
            command(*args, **kwargs)
        except DomainError as error:
            typer.echo(f"Error: {error.message}", err=True)
            raise typer.Exit(FAILURE_EXIT_CODE) from error

    return wrapper
