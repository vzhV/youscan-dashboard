from collections.abc import Sequence
from dataclasses import asdict

from app.core.errors import DuplicatePointError, NotShapeableError
from app.importing.location import describe_source
from app.importing.shaping.columns import CellIssue, ColumnKind, ColumnProfile
from app.importing.table import Table

NEEDS_NUMBER_COLUMN = "needs a number column"
NEEDS_CATEGORY_COLUMN = "needs a date or text column for the categories"
HAS_NO_DATA_ROWS = "has no data rows"


def not_shapeable(table: Table, profiles: Sequence[ColumnProfile], reason: str) -> NotShapeableError:
    message = f"{describe_source(table.name)} {reason}"
    return NotShapeableError(message, details=_details(profiles))


def cells_do_not_match(table: Table, profiles: Sequence[ColumnProfile]) -> NotShapeableError:
    """First bad cell of each column that is almost numbers or dates, so the user can fix the file."""
    issues = "; ".join(_describe_issue(issue) for issue in _issues(profiles))
    return NotShapeableError(
        f"{describe_source(table.name)} cannot be shaped: {issues}", details=_details(profiles)
    )


def _issues(profiles: Sequence[ColumnProfile]) -> list[CellIssue]:
    return [profile.first_invalid for profile in profiles if profile.first_invalid is not None]


def _details(profiles: Sequence[ColumnProfile]) -> dict[str, object]:
    return {
        "columns": [{"name": profile.name, "kind": profile.kind.value} for profile in profiles],
        "issues": [{**asdict(issue), "expected": issue.expected.value} for issue in _issues(profiles)],
    }


def unused_columns_reason(unused: Sequence[ColumnProfile]) -> str:
    listed = ", ".join(f"'{profile.name}' ({profile.kind.value})" for profile in unused)
    return f"has columns that would be dropped: {listed}"


def empty_cell(table: Table, row: int, column: str) -> NotShapeableError:
    message = f"{describe_source(table.name)}, row {row}: the '{column}' cell is empty"
    return NotShapeableError(message, details={"row": row})


def duplicate_point(table: Table, category: str, series: str | None, row: int) -> DuplicatePointError:
    subject = f"category '{category}'" if series is None else f"category '{category}' in series '{series}'"
    message = f"{describe_source(table.name)}, row {row}: duplicate value for {subject}"
    return DuplicatePointError(message, details={"category": category, "series": series, "row": row})


def _describe_issue(issue: CellIssue) -> str:
    article_noun = "a date" if issue.expected is ColumnKind.DATE else "a number"
    return f"Column '{issue.column}', row {issue.row}: '{issue.value}' is not {article_noun}"
