import pytest
from fastapi.routing import APIRoute

from app.api.openapi import generate_operation_id


async def endpoint() -> None: ...


def test_operation_id_joins_tag_and_hyphenated_route_name() -> None:
    route = APIRoute("/x", endpoint, name="update_title", tags=["widgets"])

    assert generate_operation_id(route) == "widgets-update-title"


def test_operation_id_for_untagged_route_raises_value_error_naming_the_route() -> None:
    route = APIRoute("/x", endpoint, name="update_title")

    with pytest.raises(ValueError, match="update_title"):
        generate_operation_id(route)
