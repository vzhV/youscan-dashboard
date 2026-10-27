from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

import anyio
import anyio.to_thread

from app.core.enums import DatasetOrigin, WidgetType, widget_type_of
from app.importing.parsers.registry import DEFAULT_REGISTRY, ParserRegistry
from app.importing.reader import read_tables
from app.importing.shaping.chart_rules import validate_for
from app.importing.shaping.shaper import shape_table
from app.importing.sheets import find_table
from app.importing.source_file import SourceFile
from app.importing.table import Table
from app.models import Dataset
from app.repositories.protocols import DatasetRepository, WidgetRepository
from app.schemas.common import TITLE_MAX_LENGTH
from app.schemas.dataset import DatasetRead
from app.schemas.imports import ImportResult, ImportSelection
from app.schemas.widget import WidgetRead
from app.services.mappers import to_dataset_read, to_widget_read
from app.services.records import DatasetSpec, WidgetDraft, append_widget, new_dataset
from app.services.seed import SEED_DATA_DIR, SEED_ENTRIES, SeedEntry


@dataclass(frozen=True)
class _PlannedImport:
    dataset: Dataset  # transient: built (and thinned) off the event loop, stored by the caller
    title: str
    widget_type: WidgetType


@dataclass(frozen=True)
class _ImportRequest:
    source: SourceFile
    selections: Sequence[ImportSelection]
    origin: DatasetOrigin
    registry: ParserRegistry


class ImportService:
    def __init__(
        self,
        datasets: DatasetRepository,
        widgets: WidgetRepository,
        registry: ParserRegistry = DEFAULT_REGISTRY,
    ) -> None:
        self._datasets = datasets
        self._widgets = widgets
        self._registry = registry

    async def import_file(
        self,
        source: SourceFile,
        selections: Sequence[ImportSelection],
        origin: DatasetOrigin = DatasetOrigin.UPLOAD,
    ) -> ImportResult:
        request = _ImportRequest(source, selections, origin, self._registry)
        # Everything CPU-bound and fallible happens here, before the first write: a bad selection leaves
        # nothing behind, and the event loop is never blocked.
        plans = await anyio.to_thread.run_sync(_plan_import, request)
        stored = [await self._store(plan) for plan in plans]
        return ImportResult(
            datasets=[dataset for dataset, _ in stored], widgets=[widget for _, widget in stored]
        )

    async def import_seed(self) -> ImportResult:
        entries_by_file: defaultdict[str, list[SeedEntry]] = defaultdict(list)
        for entry in SEED_ENTRIES:
            entries_by_file[entry.filename].append(entry)
        results = [await self._import_seed_file(name, entries) for name, entries in entries_by_file.items()]
        return ImportResult(
            datasets=[dataset for result in results for dataset in result.datasets],
            widgets=[widget for result in results for widget in result.widgets],
        )

    async def _import_seed_file(self, filename: str, entries: Sequence[SeedEntry]) -> ImportResult:
        content = await anyio.Path(SEED_DATA_DIR / filename).read_bytes()
        selections = [
            ImportSelection(sheet=entry.sheet, chart_type=entry.chart_type, title=entry.title)
            for entry in entries
        ]
        return await self.import_file(SourceFile(filename, content), selections, DatasetOrigin.SEED)

    async def _store(self, plan: _PlannedImport) -> tuple[DatasetRead, WidgetRead]:
        dataset = await self._datasets.add(plan.dataset)
        draft = WidgetDraft(type=plan.widget_type, title=plan.title, dataset=dataset)
        widget = await append_widget(self._widgets, draft)
        return to_dataset_read(dataset, widget_count=1), to_widget_read(widget)


def _plan_import(request: _ImportRequest) -> list[_PlannedImport]:
    tables = read_tables(request.source, request.registry)
    return [_plan_selection(request, tables, selection) for selection in request.selections]


def _plan_selection(
    request: _ImportRequest, tables: Sequence[Table], selection: ImportSelection
) -> _PlannedImport:
    table = find_table(tables, selection.sheet)
    shaped = shape_table(table)
    validate_for(selection.chart_type, shaped.data)
    default_name = (table.name or request.source.stem)[:TITLE_MAX_LENGTH]
    spec = DatasetSpec(
        name=default_name,
        origin=request.origin,
        chart_type=selection.chart_type,
        data=shaped.data,
        row_count=shaped.row_count,
        source_filename=request.source.filename,
        source_sheet=table.name,
    )
    title = selection.title or default_name
    return _PlannedImport(new_dataset(spec), title, widget_type_of(selection.chart_type))
