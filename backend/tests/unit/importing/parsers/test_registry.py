import pytest

from app.core.errors import UnsupportedFileTypeError
from app.importing.parsers.csv_parser import CsvParser
from app.importing.parsers.registry import DEFAULT_REGISTRY, ParserRegistry
from app.importing.source_file import SourceFile


def test_registry_matches_extension_case_insensitively() -> None:
    parser = DEFAULT_REGISTRY.for_file(SourceFile("DATA.CSV", b""))

    assert isinstance(parser, CsvParser)


def test_registry_unsupported_extension_lists_supported() -> None:
    with pytest.raises(UnsupportedFileTypeError) as error:
        DEFAULT_REGISTRY.for_file(SourceFile("notes.txt", b""))

    assert error.value.message == "Unsupported file type '.txt'. Supported: .csv, .xlsx"
    assert error.value.details == {"supported": [".csv", ".xlsx"]}


def test_registry_lists_supported_extensions() -> None:
    assert DEFAULT_REGISTRY.supported_extensions == {".csv", ".xlsx"}


def test_source_file_exposes_stem_and_lowercase_extension() -> None:
    source = SourceFile("Report.Final.XLSX", b"")

    assert (source.stem, source.extension) == ("Report.Final", ".xlsx")


@pytest.mark.parametrize("filename", ["data", ".csv"])
def test_registry_filename_without_extension_raises_unsupported(filename: str) -> None:
    with pytest.raises(UnsupportedFileTypeError) as error:
        DEFAULT_REGISTRY.for_file(SourceFile(filename, b""))

    assert error.value.message == "File has no extension. Supported: .csv, .xlsx"
    assert error.value.details == {"supported": [".csv", ".xlsx"]}


def test_registry_two_parsers_claiming_one_extension_raises_value_error() -> None:
    with pytest.raises(ValueError, match=r"'\.csv' is claimed by more than one parser"):
        ParserRegistry([CsvParser(), CsvParser()])
