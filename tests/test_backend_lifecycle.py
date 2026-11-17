import io
from collections.abc import Mapping
from typing import Never

import pytest

from tests.contracts import OpenResources, OwnedResource, ReadSettings


@pytest.mark.contract("validate-startup-configuration")
class TestStartupSettings:
    def test_false_string_is_not_truthy_debug(
        self, implementation: ReadSettings
    ) -> None:
        assert implementation({"PORT": "8000", "DEBUG": "false"}) == {
            "port": 8000,
            "debug": False,
        }

    @pytest.mark.parametrize("settings", [{}, {"PORT": "70000"}, {"PORT": "abc"}])
    def test_invalid_port_prevents_startup(
        self, implementation: ReadSettings, settings: Mapping[str, str]
    ) -> None:
        with pytest.raises(ValueError):
            _ = implementation(settings)


@pytest.mark.contract("own-resource-lifetimes")
class TestResourceLifetime:
    def test_owned_resource_closes_on_error(
        self, implementation: OwnedResource
    ) -> None:
        resource = io.BytesIO()

        with pytest.raises(ValueError), implementation(lambda: resource):
            raise ValueError
        assert resource.closed

    def test_resource_is_usable_inside_scope(
        self, implementation: OwnedResource
    ) -> None:
        resource = io.BytesIO()

        with implementation(lambda: resource) as borrowed:
            _ = borrowed.write(b"data")
            assert borrowed.getvalue() == b"data"
        assert resource.closed


@pytest.mark.contract("unwind-partial-startup")
class TestPartialStartup:
    def test_second_acquisition_failure_closes_first_resource(
        self, implementation: OpenResources
    ) -> None:
        first = io.BytesIO()

        def fail() -> Never:
            raise OSError("startup failed")

        with pytest.raises(OSError), implementation([lambda: first, fail]):
            pytest.fail("startup unexpectedly succeeded")
        assert first.closed

    def test_successful_resources_close_in_reverse_order(
        self, implementation: OpenResources
    ) -> None:
        closed: list[str] = []

        class Resource:
            name: str

            def __init__(self, name: str) -> None:
                self.name = name

            def close(self) -> None:
                closed.append(self.name)

        with implementation(
            [lambda: Resource("a"), lambda: Resource("b")]
        ) as resources:
            assert len(resources) == 2
        assert closed == ["b", "a"]
