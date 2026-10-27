import re
from http import HTTPStatus

from app.api.errors import STATUS_BY_ERROR, status_for
from app.core import errors
from app.core.errors import DomainError, NotFoundError

SNAKE_CASE = re.compile(r"^[a-z]+(_[a-z]+)*$")


def all_subclasses(base: type[DomainError]) -> set[type[DomainError]]:
    found: set[type[DomainError]] = set()
    for subclass in base.__subclasses__():
        # Subclasses declared inside tests linger in __subclasses__() and must not leak across tests.
        if subclass.__module__.startswith("tests."):
            continue
        found |= {subclass} | all_subclasses(subclass)
    return found


def test_every_domain_error_subclass_has_an_http_status() -> None:
    subclasses = all_subclasses(DomainError)

    assert subclasses
    assert subclasses <= set(STATUS_BY_ERROR)


def test_every_domain_error_code_is_unique_snake_case() -> None:
    codes = [subclass.code for subclass in all_subclasses(DomainError)]

    assert len(codes) == len(set(codes))
    assert all(SNAKE_CASE.match(code) for code in codes)


def test_catalog_module_is_the_source_of_all_subclasses() -> None:
    assert all(subclass.__module__ == errors.__name__ for subclass in all_subclasses(DomainError))


def test_status_for_resolves_subclasses_through_the_mro() -> None:
    class MissingWidgetError(NotFoundError):
        code = "missing_widget"

    assert status_for(MissingWidgetError("gone")) == 404


def test_seed_data_error_maps_to_500_with_its_own_code() -> None:
    assert status_for(errors.SeedDataError("bad")) == HTTPStatus.INTERNAL_SERVER_ERROR
    assert errors.SeedDataError.code == "seed_data_invalid"
