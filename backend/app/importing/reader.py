from app.core.errors import InvalidFileError
from app.importing.limits import DEFAULT_LIMITS, ImportLimits
from app.importing.parsers.registry import DEFAULT_REGISTRY, ParserRegistry
from app.importing.source_file import SourceFile
from app.importing.table import Table


def read_tables(
    source: SourceFile,
    registry: ParserRegistry = DEFAULT_REGISTRY,
    limits: ImportLimits = DEFAULT_LIMITS,
) -> list[Table]:
    # Parsers enforce the limits while streaming, so oversized files are rejected before they are loaded.
    tables = registry.for_file(source).parse(source.content, limits)
    if not tables:
        raise InvalidFileError("File contains no data")
    return tables
