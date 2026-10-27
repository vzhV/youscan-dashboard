import json
import runpy
import sys
from pathlib import Path

import pytest

from app.openapi_export import export_openapi


def test_openapi_export_module_writes_the_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "openapi.json"
    monkeypatch.setattr("sys.argv", ["app.openapi_export", str(output)])
    # runpy warns when the module it runs as __main__ is already imported (by this file's top-level import).
    monkeypatch.delitem(sys.modules, "app.openapi_export")

    with pytest.raises(SystemExit) as stopped:
        runpy.run_module("app.openapi_export", run_name="__main__")

    assert stopped.value.code == 0
    operation_ids = {
        operation["operationId"]
        for item in json.loads(output.read_text())["paths"].values()
        for operation in item.values()
    }
    assert {"imports-preview", "imports-create", "widgets-list"} <= operation_ids


def test_export_openapi_writes_valid_json(tmp_path: Path) -> None:
    output = tmp_path / "schema.json"

    export_openapi(output)

    assert json.loads(output.read_text())["info"]["title"] == "Dashboard API"
