from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine


async def list_table_names(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as connection:
        return set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))


async def test_migrations_upgrade_downgrade_upgrade_roundtrip(
    engine: AsyncEngine, alembic_config: Config
) -> None:
    # Pooled connections cache prepared statements and type OIDs that the DROP/CREATE below invalidates.
    await engine.dispose()
    command.downgrade(alembic_config, "base")
    tables_at_base = await list_table_names(engine)
    command.upgrade(alembic_config, "head")
    tables_at_head = await list_table_names(engine)

    assert {"datasets", "widgets"}.isdisjoint(tables_at_base)
    assert {"datasets", "widgets"} <= tables_at_head
