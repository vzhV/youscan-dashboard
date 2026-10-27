from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, routing
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from httpx import AsyncClient
from starlette.routing import Route

from app.api.deps import get_session

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head"}
API_PREFIX = "/api/v1"
NO_CONTENT = "204"


def operations(app: FastAPI) -> list[tuple[str, dict[str, Any]]]:
    paths: dict[str, dict[str, Any]] = app.openapi()["paths"]
    return [
        (f"{method.upper()} {path}", operation)
        for path, item in paths.items()
        for method, operation in item.items()
        if method in HTTP_METHODS
    ]


def api_routes(app: FastAPI) -> list[APIRoute]:
    """Walk what is actually mounted, the same way FastAPI's own openapi() does."""
    contexts = routing.iter_route_contexts(app.routes)
    return [context.original_route for context in contexts if isinstance(context.original_route, APIRoute)]


async def test_docs_and_schema_are_served_under_api_prefix(client: AsyncClient) -> None:
    assert (await client.get(f"{API_PREFIX}/docs")).status_code == 200
    assert (await client.get(f"{API_PREFIX}/redoc")).status_code == 200
    assert (await client.get(f"{API_PREFIX}/openapi.json")).status_code == 200
    assert (await client.get("/docs")).status_code == 404


def test_every_registered_path_lives_under_api_prefix(app: FastAPI) -> None:
    plain_paths = [route.path for route in app.routes if isinstance(route, Route)]
    schema_paths = list(app.openapi()["paths"])

    assert all(path.startswith(API_PREFIX) for path in plain_paths + schema_paths)


def test_every_operation_has_summary_description_and_one_tag(app: FastAPI) -> None:
    for name, operation in operations(app):
        assert operation.get("summary"), f"{name} has no summary"
        assert operation.get("description"), f"{name} has no description (add a docstring)"
        assert len(operation.get("tags", [])) == 1, f"{name} must have exactly one tag"


def test_every_route_declares_a_status_code(app: FastAPI) -> None:
    routes = api_routes(app)

    assert routes
    for route in routes:
        assert route.status_code is not None, f"{route.name} must declare status_code"


def test_every_success_response_has_a_schema_unless_no_content(app: FastAPI) -> None:
    for name, operation in operations(app):
        for status, response in operation["responses"].items():
            if status.startswith("2") and status != NO_CONTENT:
                assert "content" in response, f"{name} {status} has no response schema"


def test_every_error_response_uses_error_response_schema(app: FastAPI) -> None:
    schema = app.openapi()
    for name, operation in operations(app):
        for status, response in operation["responses"].items():
            if status.startswith("2"):
                continue
            ref = response["content"]["application/json"]["schema"]["$ref"]
            assert ref.endswith("/ErrorResponse"), f"{name} {status} uses {ref}"
    assert "HTTPValidationError" not in str(schema)


def test_every_schema_property_has_a_description_and_examples(app: FastAPI) -> None:
    schemas: dict[str, dict[str, Any]] = app.openapi()["components"]["schemas"]
    for schema_name, schema in schemas.items():
        for property_name, property_schema in schema.get("properties", {}).items():
            location = f"{schema_name}.{property_name}"
            assert property_schema.get("description"), f"{location} has no description"
            assert property_schema.get("examples"), f"{location} has no examples"


def depends_on(dependant: Dependant, target: object) -> bool:
    return any(
        dependency.call is target or depends_on(dependency, target) for dependency in dependant.dependencies
    )


def test_every_database_route_documents_service_unavailable(app: FastAPI) -> None:
    routes = [route for route in api_routes(app) if depends_on(route.dependant, get_session)]

    assert routes
    for route in routes:
        assert HTTPStatus.SERVICE_UNAVAILABLE in route.responses, f"{route.name} must document 503"
