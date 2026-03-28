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

"""UT1.8: Logger Factory — get_logger and get_audit_logger tests."""

from __future__ import annotations

from cloud_dog_logging import get_logger, get_audit_logger, setup_logging
from cloud_dog_logging.app_logger import AppLogger
from cloud_dog_logging.audit_logger import AuditLogger


class TestLoggerFactory:
    """Test suite for logger factory functions."""

    def test_get_logger_returns_app_logger(self) -> None:
        logger = get_logger("test.module")
        assert isinstance(logger, AppLogger)

    def test_get_logger_name_matches(self) -> None:
        logger = get_logger("my.module.name")
        assert logger.name == "my.module.name"

    def test_get_audit_logger_returns_audit_logger(self) -> None:
        audit = get_audit_logger()
        assert isinstance(audit, AuditLogger)

    def test_get_audit_logger_singleton(self) -> None:
        a1 = get_audit_logger()
        a2 = get_audit_logger()
        assert a1 is a2

    def test_get_logger_after_setup(self) -> None:
        setup_logging({"service_name": "factory-test", "log": {"level": "DEBUG"}})
        logger = get_logger("test.after_setup")
        assert isinstance(logger, AppLogger)

    def test_get_audit_logger_after_setup(self) -> None:
        setup_logging({"service_name": "factory-test"})
        audit = get_audit_logger()
        assert isinstance(audit, AuditLogger)

    def test_multiple_loggers_independent(self) -> None:
        l1 = get_logger("module.a")
        l2 = get_logger("module.b")
        assert l1.name != l2.name
