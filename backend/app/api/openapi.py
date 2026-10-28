from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from app.schemas.imports import ImportSelection

TAGS_METADATA: list[dict[str, str]] = [
    {"name": "health", "description": "Liveness and database connectivity."},
    {"name": "widgets", "description": "Create, rename, edit and delete widgets, and read their chart data."},
    {
        "name": "datasets",
        "description": (
            "Seeded and uploaded datasets: list them, add one to the dashboard again, "
            "or delete one with its widgets."
        ),
    },
    {"name": "imports", "description": "Two-step file import: inspect a file, then confirm it."},
    {"name": "dashboard", "description": "Board-level operations such as reset to the seeded state."},
]


def generate_operation_id(route: APIRoute) -> str:
    if not route.tags:
        raise ValueError(f"Route {route.path} ({route.name}) needs a tag to build its operation id")
    return f"{route.tags[0]}-{route.name.replace('_', '-')}"


class DashboardApi(FastAPI):
    """FastAPI app whose OpenAPI document also lists ImportSelection.

    The import endpoint takes `selections` as a JSON string in a multipart form, so FastAPI never sees the
    model; registering it here lets the frontend generate its type instead of mirroring it by hand.
    """

    def openapi(self) -> dict[str, Any]:
        if self.openapi_schema:
            return self.openapi_schema
        schema = super().openapi()
        selection_schema = ImportSelection.model_json_schema(ref_template="#/components/schemas/{model}")
        definitions = selection_schema.pop("$defs", {})
        schemas: dict[str, Any] = schema.setdefault("components", {}).setdefault("schemas", {})
        for name, definition in {**definitions, ImportSelection.__name__: selection_schema}.items():
            schemas.setdefault(name, definition)
        return schema
