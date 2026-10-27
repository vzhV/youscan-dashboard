from collections.abc import Mapping, Sequence
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook

SEED_DATA_DIR = Path(__file__).resolve().parents[1] / "seed_data"


def make_xlsx(sheets: Mapping[str, Sequence[Sequence[object]]]) -> bytes:
    workbook = Workbook(write_only=True)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def make_xlsx_with_cells(
    name: str, rows: Sequence[Sequence[object]], extra_cells: Mapping[str, str | float]
) -> bytes:
    """Single-sheet workbook with cells set by coordinate.

    Unlike make_xlsx this is not write-only, so the file declares a <dimension> covering the
    far-away cells, which is what makes read-only rows come back padded.
    """
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = name
    for row in rows:
        sheet.append(list(row))
    for coordinate, value in extra_cells.items():
        sheet[coordinate] = value
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def make_zip(members: Mapping[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for member, data in members.items():
            archive.writestr(member, data)
    return buffer.getvalue()


def replace_zip_member(archive_bytes: bytes, member: str, data: bytes) -> bytes:
    with ZipFile(BytesIO(archive_bytes)) as archive:
        members = {item: archive.read(item) for item in archive.namelist()}
    members[member] = data
    return make_zip(members)
