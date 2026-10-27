import csv
from _csv import Reader
from collections.abc import Iterator
from io import StringIO

from app.core.errors import InvalidFileError
from app.importing.limits import ImportLimits
from app.importing.table import Table, build_table

SNIFF_SAMPLE_CHARS = 4096
CANDIDATE_DELIMITERS = ",;\t"
DEFAULT_DELIMITER = ","


class CsvParser:
    extensions = frozenset({".csv"})

    def parse(self, content: bytes, limits: ImportLimits) -> list[Table]:
        text = _decode(content)
        # newline="" lets the csv module see raw line endings, so CR-only files and quoted newlines work.
        reader = csv.reader(StringIO(text, newline=""), delimiter=_sniff_delimiter(text))
        table = build_table(None, _numbered(reader), limits)
        return [table] if table else []


def _numbered(reader: Reader) -> Iterator[tuple[int, list[str]]]:
    # A quoted field can span lines, so a record starts on the line after the previous record ended.
    previous_end = 0
    while True:
        try:
            cells = next(reader)
        except StopIteration:
            return
        except csv.Error as error:
            # Report where the broken record began; the reader only notices at the end of the overflow.
            raise InvalidFileError(f"Could not read the CSV near line {previous_end + 1}: {error}") from error
        yield previous_end + 1, cells
        previous_end = reader.line_num


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InvalidFileError("File must be UTF-8 encoded. In Excel, save it as 'CSV UTF-8'.") from error


def _sniff_delimiter(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text[:SNIFF_SAMPLE_CHARS], delimiters=CANDIDATE_DELIMITERS).delimiter
    except csv.Error:
        return DEFAULT_DELIMITER
