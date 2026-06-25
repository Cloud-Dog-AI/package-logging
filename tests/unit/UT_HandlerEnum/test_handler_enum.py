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

"""UT_HandlerEnum — public ``HandlerType`` enum (#A39 piece 3).

Verifies that the previously-internal ``HandlerType`` enum is now part of
the package's public surface, that ``LogConfig.from_dict`` correctly
threads the ``log.handlers`` and ``log.extra_fields`` keys through, and
that ``setup_logging`` honours both knobs.

Related requirements: FR1.11
Related architecture: CC1.9
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

import cloud_dog_logging
from cloud_dog_logging import HandlerType, LogConfig, setup_logging
from cloud_dog_logging.handlers.dual_handler import DualHandler
from cloud_dog_logging.handlers.rotating_file import ConfigurableRotatingHandler
from cloud_dog_logging.handlers.stdout_handler import StdoutHandler


class TestPublicAPIExposed:
    def test_handler_type_is_public(self) -> None:
        assert cloud_dog_logging.HandlerType is HandlerType

    def test_handler_type_members_are_stable_strings(self) -> None:
        assert HandlerType.FILE.value == "file"
        assert HandlerType.CONSOLE.value == "console"
        assert HandlerType.DUAL.value == "dual"
        assert HandlerType.ROTATING.value == "rotating"


class TestHandlerTypeCoercion:
    def test_coerce_string(self) -> None:
        assert HandlerType.coerce("dual") is HandlerType.DUAL
        assert HandlerType.coerce("CONSOLE") is HandlerType.CONSOLE
        assert HandlerType.coerce(" file ") is HandlerType.FILE

    def test_coerce_member_passthrough(self) -> None:
        assert HandlerType.coerce(HandlerType.ROTATING) is HandlerType.ROTATING

    def test_coerce_unknown_raises(self) -> None:
        with pytest.raises(ValueError):
            HandlerType.coerce("syslog")

    def test_coerce_many_handles_none(self) -> None:
        assert HandlerType.coerce_many(None) == []

    def test_coerce_many_mixed_input(self) -> None:
        result = HandlerType.coerce_many(["dual", HandlerType.FILE])
        assert result == [HandlerType.DUAL, HandlerType.FILE]


class TestLogConfigHandlersThreading:
    """Regression: 0.3.4 read ``log.handlers`` from dict but never reached
    the dataclass constructor. After A39 the value MUST round-trip."""

    def test_handlers_from_dict_round_trip(self) -> None:
        cfg = LogConfig.from_dict({"log": {"handlers": ["dual"]}})
        assert cfg.handlers == ["dual"]

    def test_handlers_string_to_list(self) -> None:
        cfg = LogConfig.from_dict({"log": {"handlers": "console"}})
        assert cfg.handlers == ["console"]

    def test_handlers_handlertype_member_normalised(self) -> None:
        cfg = LogConfig.from_dict({"log": {"handlers": [HandlerType.DUAL]}})
        assert cfg.handlers == ["dual"]

    def test_extra_fields_from_dict_round_trip(self) -> None:
        cfg = LogConfig.from_dict({"log": {"extra_fields": ["server_id", "request_id"]}})
        assert cfg.extra_fields == ["server_id", "request_id"]

    def test_extra_fields_string_to_list(self) -> None:
        cfg = LogConfig.from_dict({"log": {"extra_fields": "server_id"}})
        assert cfg.extra_fields == ["server_id"]


class TestSetupLoggingWithHandlerType:
    """``setup_logging`` honours the declarative ``handlers`` selection."""

    def test_console_only(self, tmp_path: Path) -> None:
        setup_logging(
            {
                "log": {
                    "handlers": ["console"],
                    "console": True,
                    "format": "json",
                    "integrity": {"enabled": False},
                },
                "service_name": "ut",
                "service_instance": "ut0",
                "environment": "ut",
            }
        )
        root = logging.getLogger()
        # Exactly one handler — the stdout one.
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], StdoutHandler)

    def test_dual_when_app_log_set(self, tmp_path: Path) -> None:
        log_file = tmp_path / "app.log"
        setup_logging(
            {
                "log": {
                    "handlers": ["dual"],
                    "console": True,
                    "format": "json",
                    "app_log": str(log_file),
                    "integrity": {"enabled": False},
                },
                "service_name": "ut",
                "service_instance": "ut0",
                "environment": "ut",
            }
        )
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], DualHandler)

    def test_file_only(self, tmp_path: Path) -> None:
        log_file = tmp_path / "app.log"
        setup_logging(
            {
                "log": {
                    "handlers": ["file"],
                    "console": False,
                    "format": "json",
                    "app_log": str(log_file),
                    "integrity": {"enabled": False},
                },
                "service_name": "ut",
                "service_instance": "ut0",
                "environment": "ut",
            }
        )
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], ConfigurableRotatingHandler)

    def test_rotating_alias_of_file(self, tmp_path: Path) -> None:
        """``ROTATING`` is documented as an alias of ``FILE`` because the
        only file-handler implementation is rotating."""
        log_file = tmp_path / "app.log"
        setup_logging(
            {
                "log": {
                    "handlers": ["rotating"],
                    "console": False,
                    "format": "json",
                    "app_log": str(log_file),
                    "integrity": {"enabled": False},
                },
                "service_name": "ut",
                "service_instance": "ut0",
                "environment": "ut",
            }
        )
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], ConfigurableRotatingHandler)

    def test_legacy_no_handlers_key_preserves_prior_behaviour(self, tmp_path: Path) -> None:
        """No ``log.handlers`` key supplied → behave exactly as 0.3.4."""
        log_file = tmp_path / "app.log"
        setup_logging(
            {
                "log": {
                    "console": True,
                    "format": "json",
                    "app_log": str(log_file),
                    "integrity": {"enabled": False},
                },
                "service_name": "ut",
                "service_instance": "ut0",
                "environment": "ut",
            }
        )
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], DualHandler)

    def test_extra_fields_threaded_into_jsonformatter(self, tmp_path: Path) -> None:
        from cloud_dog_logging.formatters.json_formatter import JSONFormatter

        log_file = tmp_path / "app.log"
        setup_logging(
            {
                "log": {
                    "handlers": ["console"],
                    "console": True,
                    "format": "json",
                    "extra_fields": ["server_id"],
                    "integrity": {"enabled": False},
                },
                "service_name": "ut",
                "service_instance": "ut0",
                "environment": "ut",
            }
        )
        root = logging.getLogger()
        formatter = root.handlers[0].formatter
        assert isinstance(formatter, JSONFormatter)
        # The promotion list MUST contain server_id.
        assert "server_id" in formatter._extra_fields
