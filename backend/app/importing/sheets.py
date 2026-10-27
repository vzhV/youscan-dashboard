from collections.abc import Sequence

from app.core.errors import SheetNotFoundError
from app.importing.table import Table


def sheet_not_found(sheet: str, names: Sequence[str | None]) -> SheetNotFoundError:
    # A CSV table has no name, so "available" never lists null.
    available = [name for name in names if name is not None]
    hint = "" if available else ": CSV files have no sheets"
    return SheetNotFoundError(f"Sheet '{sheet}' not found{hint}", details={"available": available})


def find_table(tables: Sequence[Table], sheet: str | None) -> Table:
    """The table for a sheet name; None means the first table."""
    if sheet is None:
        return tables[0]
    for table in tables:
        if table.name == sheet:
            return table
    raise sheet_not_found(sheet, [table.name for table in tables])
