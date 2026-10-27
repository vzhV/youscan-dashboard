from typing import Protocol

from app.importing.limits import ImportLimits
from app.importing.table import Table


class FileParser(Protocol):
    extensions: frozenset[str]

    def parse(self, content: bytes, limits: ImportLimits) -> list[Table]: ...
