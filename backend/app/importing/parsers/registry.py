from collections.abc import Sequence

from app.core.errors import UnsupportedFileTypeError
from app.importing.parsers.base import FileParser
from app.importing.parsers.csv_parser import CsvParser
from app.importing.parsers.xlsx_parser import XlsxParser
from app.importing.source_file import SourceFile


class ParserRegistry:
    def __init__(self, parsers: Sequence[FileParser]) -> None:
        self._by_extension: dict[str, FileParser] = {}
        for parser in parsers:
            for extension in parser.extensions:
                if extension in self._by_extension:
                    raise ValueError(f"Extension '{extension}' is claimed by more than one parser")
                self._by_extension[extension] = parser

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset(self._by_extension)

    def for_file(self, source: SourceFile) -> FileParser:
        parser = self._by_extension.get(source.extension)
        if parser is not None:
            return parser
        supported = sorted(self.supported_extensions)
        listed = ", ".join(supported)
        problem = (
            f"Unsupported file type '{source.extension}'" if source.extension else "File has no extension"
        )
        raise UnsupportedFileTypeError(f"{problem}. Supported: {listed}", details={"supported": supported})


DEFAULT_REGISTRY = ParserRegistry([CsvParser(), XlsxParser()])
