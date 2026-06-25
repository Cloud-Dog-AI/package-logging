# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""UT_JSONFieldRegistry — public JSONFormatter field-hook (#A39 piece 2).

Verifies the ``add_json_field`` registry that lets services contribute
top-level JSON fields without subclassing or monkey-patching
``JSONFormatter``. Closes the architectural ceiling notification-agent's
``logger.py`` ``_ensure_json_formatter_patch`` was working around.

Related requirements: FR1.2, FR1.4
Related architecture: CC1.6
"""

from __future__ import annotations

import json
import logging

import pytest

import cloud_dog_logging
from cloud_dog_logging import (
    JSONFormatter,
    add_json_field,
    clear_json_fields,
    get_registered_json_fields,
    remove_json_field,
)


@pytest.fixture(autouse=True)
def _isolate_json_field_registry() -> None:
    """Each test starts with an empty registry."""
    clear_json_fields()


def _format_json(formatter: JSONFormatter, *, message: str = "msg", level: int = logging.INFO) -> dict:
    py_logger = logging.getLogger("ut.json.registry")
    record = py_logger.makeRecord("ut.json.registry", level, "test.py", 1, message, (), None)
    return json.loads(formatter.format(record))


class TestPublicAPIExposed:
    def test_add_json_field_is_public(self) -> None:
        assert callable(cloud_dog_logging.add_json_field)

    def test_remove_json_field_is_public(self) -> None:
        assert callable(cloud_dog_logging.remove_json_field)

    def test_clear_json_fields_is_public(self) -> None:
        assert callable(cloud_dog_logging.clear_json_fields)

    def test_get_registered_json_fields_is_public(self) -> None:
        assert callable(cloud_dog_logging.get_registered_json_fields)

    def test_json_field_provider_alias_is_public(self) -> None:
        assert cloud_dog_logging.JSONFieldProvider is not None


class TestJSONFieldRegistry:
    def test_registered_field_appears_in_output(self) -> None:
        add_json_field("severity", lambda record: record.levelname)
        formatter = JSONFormatter(service_name="ut")
        out = _format_json(formatter, level=logging.WARNING)
        assert out["severity"] == "WARNING"

    def test_multiple_fields_compose(self) -> None:
        add_json_field("severity", lambda record: record.levelname)
        add_json_field("event_type", lambda record: "ut.event")
        formatter = JSONFormatter(service_name="ut")
        out = _format_json(formatter)
        assert out["severity"] == "INFO"
        assert out["event_type"] == "ut.event"

    def test_remove_json_field(self) -> None:
        add_json_field("temp", lambda record: "alive")
        formatter = JSONFormatter(service_name="ut")
        first = _format_json(formatter)
        assert first["temp"] == "alive"
        assert remove_json_field("temp") is True
        second = _format_json(formatter)
        assert "temp" not in second

    def test_remove_unknown_returns_false(self) -> None:
        assert remove_json_field("never-registered") is False

    def test_clear_json_fields(self) -> None:
        add_json_field("a", lambda record: 1)
        add_json_field("b", lambda record: 2)
        assert set(get_registered_json_fields()) == {"a", "b"}
        clear_json_fields()
        assert get_registered_json_fields() == {}

    def test_stable_schema_field_names_rejected(self) -> None:
        for name in (
            "timestamp",
            "level",
            "logger",
            "message",
            "correlation_id",
            "service",
            "service_instance",
            "environment",
            "extra",
            "traceback",
            "stack_info",
        ):
            with pytest.raises(ValueError):
                add_json_field(name, lambda record, _n=name: "should not work")

    def test_non_callable_provider_rejected(self) -> None:
        with pytest.raises(TypeError):
            add_json_field("bad", "not-callable")  # type: ignore[arg-type]

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError):
            add_json_field("", lambda record: "value")

    def test_provider_exception_swallowed(self) -> None:
        def _broken(record: logging.LogRecord) -> str:
            raise RuntimeError("provider explosion")

        add_json_field("brittle", _broken)
        formatter = JSONFormatter(service_name="ut")
        out = _format_json(formatter)
        # The line MUST still be valid JSON and MUST omit the broken field.
        assert "brittle" not in out
        assert out["service"] == "ut"

    def test_provider_returning_none_is_skipped(self) -> None:
        add_json_field("optional", lambda record: None)
        formatter = JSONFormatter(service_name="ut")
        out = _format_json(formatter)
        assert "optional" not in out

    def test_non_serialisable_value_coerced_to_string(self) -> None:
        class Opaque:
            def __str__(self) -> str:
                return "opaque-repr"

        add_json_field("opaque", lambda record: Opaque())
        formatter = JSONFormatter(service_name="ut")
        out = _format_json(formatter)
        assert out["opaque"] == "opaque-repr"

    def test_idempotent_rebind(self) -> None:
        add_json_field("ver", lambda record: "v1")
        formatter = JSONFormatter(service_name="ut")
        first = _format_json(formatter)
        assert first["ver"] == "v1"
        add_json_field("ver", lambda record: "v2")
        second = _format_json(formatter)
        assert second["ver"] == "v2"

    def test_no_overwrite_of_stable_schema_via_provider(self) -> None:
        """Defence in depth: even if a provider sneaks past the registration
        guard, ``JSONFormatter.format`` must NEVER overwrite a stable schema
        field. This proves the second guard inside ``format``."""
        from cloud_dog_logging.formatters.json_formatter import _json_field_providers, _json_field_lock

        with _json_field_lock:
            _json_field_providers["service"] = lambda record: "BYPASS-ATTEMPT"
        try:
            formatter = JSONFormatter(service_name="ut-service")
            out = _format_json(formatter)
            # The stable schema "service" value must still be the formatter's.
            assert out["service"] == "ut-service"
        finally:
            with _json_field_lock:
                _json_field_providers.pop("service", None)


class TestNotificationAgentJSONParity:
    """End-to-end: the registry replaces the wrapper's monkey-patch.

    notification-agent's ``_ensure_json_formatter_patch`` reaches into
    ``JSONFormatter.format`` and adds ``severity`` and ``event_type``
    after-the-fact. Using only the public API achieves the same output
    shape — so the wrapper can be deleted in the follow-on per-service
    atomic.
    """

    def test_full_parity_shape(self) -> None:
        add_json_field("severity", lambda record: record.levelname)
        add_json_field("event_type", lambda record: "application.event")

        formatter = JSONFormatter(service_name="notification-agent")
        out = _format_json(formatter)

        assert out["severity"] == "INFO"
        assert out["event_type"] == "application.event"
        # Stable schema preserved
        assert out["service"] == "notification-agent"
        assert "timestamp" in out
        assert "level" in out
        assert "logger" in out
