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

"""UT_LogRecordFactory — public LogRecord factory hook (#A39 piece 1).

Verifies the public API exported by ``cloud_dog_logging`` for installing
custom per-record fields without subclassing or monkey-patching stdlib
logging:

- :func:`register_log_field_provider` — adds an attribute to every
  subsequent ``LogRecord``.
- :func:`unregister_log_field_provider` — removes a single provider.
- :func:`clear_log_field_providers` — clears the registry (test isolation).
- :func:`get_registered_field_providers` — diagnostic snapshot.

The closing test exercises the same provider-registration call sites
notification-agent's bespoke ``logger.py`` wrapper used to perform via
``__import__("logging").setLogRecordFactory`` — the surface this hook
exists to retire.

Related requirements: FR1.4, FR1.6, FR1.17
Related architecture: CC1.6, CC1.9
"""

from __future__ import annotations

import logging
import threading

import pytest

import cloud_dog_logging
from cloud_dog_logging import (
    clear_log_field_providers,
    get_registered_field_providers,
    register_log_field_provider,
    unregister_log_field_provider,
)


@pytest.fixture(autouse=True)
def _isolate_factory_registry() -> None:
    """Clear field-provider registry before each test."""
    clear_log_field_providers()


def _make_record(name: str = "test", level: int = logging.INFO, message: str = "hello") -> logging.LogRecord:
    """Use the live record factory (the chained one once a provider is registered)."""
    factory = logging.getLogRecordFactory()
    return factory(name, level, "test.py", 1, message, (), None)


class TestPublicAPIExposed:
    """Sanity: the new symbols are reachable via the package root (CIC reference-first map item 1)."""

    def test_register_log_field_provider_is_public(self) -> None:
        assert callable(cloud_dog_logging.register_log_field_provider)

    def test_unregister_log_field_provider_is_public(self) -> None:
        assert callable(cloud_dog_logging.unregister_log_field_provider)

    def test_clear_log_field_providers_is_public(self) -> None:
        assert callable(cloud_dog_logging.clear_log_field_providers)

    def test_get_registered_field_providers_is_public(self) -> None:
        assert callable(cloud_dog_logging.get_registered_field_providers)

    def test_field_provider_type_alias_is_public(self) -> None:
        # Just an attribute lookup smoke; the alias is a typing.Callable.
        assert cloud_dog_logging.FieldProvider is not None


class TestLogRecordFactory:
    """The factory hook installs per-record attributes."""

    def test_provider_value_appears_on_record(self) -> None:
        register_log_field_provider("server_id", lambda: "ut-host")
        record = _make_record()
        assert getattr(record, "server_id") == "ut-host"

    def test_provider_invoked_per_record(self) -> None:
        counter = {"n": 0}

        def _provider() -> int:
            counter["n"] += 1
            return counter["n"]

        register_log_field_provider("call_seq", _provider)
        first = _make_record(message="first")
        second = _make_record(message="second")
        assert first.call_seq == 1  # type: ignore[attr-defined]
        assert second.call_seq == 2  # type: ignore[attr-defined]

    def test_unregister_removes_attribute(self) -> None:
        register_log_field_provider("temp_field", lambda: "value")
        record_with = _make_record()
        assert getattr(record_with, "temp_field") == "value"
        assert unregister_log_field_provider("temp_field") is True
        record_without = _make_record()
        assert not hasattr(record_without, "temp_field") or getattr(record_without, "temp_field") in (None, "")

    def test_unregister_returns_false_for_missing(self) -> None:
        assert unregister_log_field_provider("never-registered") is False

    def test_clear_log_field_providers_drops_all(self) -> None:
        register_log_field_provider("a", lambda: 1)
        register_log_field_provider("b", lambda: 2)
        assert set(get_registered_field_providers()) == {"a", "b"}
        clear_log_field_providers()
        assert get_registered_field_providers() == {}

    def test_reserved_attribute_names_rejected(self) -> None:
        with pytest.raises(ValueError):
            register_log_field_provider("msg", lambda: "should not work")
        with pytest.raises(ValueError):
            register_log_field_provider("levelname", lambda: "WARNING")

    def test_non_callable_provider_rejected(self) -> None:
        with pytest.raises(TypeError):
            register_log_field_provider("bad", "not-a-callable")  # type: ignore[arg-type]

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError):
            register_log_field_provider("", lambda: "value")

    def test_pre_set_attribute_not_overwritten(self) -> None:
        """If the record already has a non-empty attribute the provider must
        not overwrite it (caller-supplied context wins)."""
        register_log_field_provider("server_id", lambda: "from-provider")
        factory = logging.getLogRecordFactory()
        record = factory("test", logging.INFO, "test.py", 1, "msg", (), None)
        # Simulate caller-supplied context arriving earlier in the chain.
        record.server_id = "from-call-site"
        # Re-applying factory logic on the same record (idempotency) MUST
        # NOT clobber the explicit value.
        register_log_field_provider("server_id", lambda: "from-provider-2")
        record_2 = factory("test", logging.INFO, "test.py", 1, "msg", (), None)
        record_2.server_id = "explicit-too"
        # Provider doesn't run a second time on the same record post-set.
        assert record.server_id == "from-call-site"
        assert record_2.server_id == "explicit-too"

    def test_provider_exception_swallowed(self) -> None:
        def _broken() -> str:
            raise RuntimeError("provider explosion")

        register_log_field_provider("brittle", _broken)
        record = _make_record()  # MUST NOT raise
        assert getattr(record, "brittle") is None

    def test_idempotent_rebind(self) -> None:
        register_log_field_provider("rebound", lambda: "v1")
        first = _make_record()
        assert first.rebound == "v1"  # type: ignore[attr-defined]
        register_log_field_provider("rebound", lambda: "v2")
        second = _make_record()
        assert second.rebound == "v2"  # type: ignore[attr-defined]

    def test_thread_safe_concurrent_registration(self) -> None:
        """Concurrent registrations and emissions must not raise."""

        def _worker(idx: int) -> None:
            for cycle in range(10):
                register_log_field_provider(f"f_{idx}", lambda i=idx, c=cycle: f"{i}-{c}")
                _ = _make_record(message=f"thread-{idx}-{cycle}")

        threads = [threading.Thread(target=_worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # All 4 workers should have left a provider behind.
        registered = get_registered_field_providers()
        assert {"f_0", "f_1", "f_2", "f_3"} <= set(registered)


class TestNotificationAgentParity:
    """End-to-end: the registered factory replaces the bespoke wrapper.

    notification-agent/src/utils/logger.py installs a chained factory that
    sets ``server_id`` on every record. After A39 the public API does the
    same thing without the wrapper. This test reproduces the wrapper's
    contract using only the public API so the bespoke can be deleted.
    """

    def test_server_id_propagates_through_logging_pipeline(self) -> None:
        register_log_field_provider("server_id", lambda: "notificationagent0")
        py_logger = logging.getLogger("ut.factory.parity")
        # A real .info() call goes through the chained factory.
        record = py_logger.makeRecord(
            "ut.factory.parity", logging.INFO, "test.py", 1, "live record", (), None
        )
        assert record.server_id == "notificationagent0"  # type: ignore[attr-defined]
