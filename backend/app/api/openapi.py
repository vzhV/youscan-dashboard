from fastapi.routing import APIRoute

TAGS_METADATA: list[dict[str, str]] = [
    {"name": "health", "description": "Liveness and database connectivity."},
    {"name": "widgets", "description": "Create, rename, edit, delete and reorder dashboard widgets."},
    {"name": "datasets", "description": "Datasets that back chart widgets."},
    {"name": "imports", "description": "Two-step file import: inspect a file, then confirm it."},
    {"name": "dashboard", "description": "Board-level operations such as reset to the seeded state."},
]


def generate_operation_id(route: APIRoute) -> str:
    if not route.tags:
        raise ValueError(f"Route {route.path} ({route.name}) needs a tag to build its operation id")
    return f"{route.tags[0]}-{route.name.replace('_', '-')}"
