"""Write the API's OpenAPI schema to a file, for client generation: `python -m app.openapi_export OUTPUT`."""

import json
from pathlib import Path
from typing import Annotated

import typer

from app.main import app

OPENAPI_INDENT = 2


def export_openapi(
    output: Annotated[Path, typer.Argument(dir_okay=False, help="File to write the OpenAPI JSON to.")],
) -> None:
    output.write_text(json.dumps(app.openapi(), indent=OPENAPI_INDENT) + "\n")


def main() -> None:
    typer.run(export_openapi)


if __name__ == "__main__":
    main()
