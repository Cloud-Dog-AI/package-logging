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

"""AT1.1: Service Startup Pattern — simulate real service startup."""

from __future__ import annotations

from pathlib import Path

from cloud_dog_logging import setup_logging, get_logger, get_audit_logger
from cloud_dog_logging.app_logger import AppLogger
from cloud_dog_logging.audit_logger import AuditLogger
from cloud_dog_logging.config import LogConfig
from cloud_dog_logging.correlation import set_correlation_id


class TestServiceStartupPattern:
    """Test suite simulating real service startup."""

    def test_setup_logging_creates_two_streams(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        audit_log = str(tmp_path / "audit.log.jsonl")

        setup_logging(
            {
                "service_name": "my-service",
                "log": {
                    "level": "DEBUG",
                    "format": "json",
                    "app_log": app_log,
                    "audit_log": audit_log,
                    "console": False,
                },
            }
        )

        logger = get_logger("my_service.main")
        assert isinstance(logger, AppLogger)

        audit = get_audit_logger()
        assert isinstance(audit, AuditLogger)

    def test_get_logger_returns_configured_logger(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "configured-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        set_correlation_id("startup-001")

        logger = get_logger("my_service.handlers")
        logger.info("Handler initialised")

        content = Path(app_log).read_text()
        assert "Handler initialised" in content

    def test_config_from_dict(self) -> None:
        config = LogConfig.from_dict(
            {
                "service_name": "dict-service",
                "log": {
                    "level": "WARNING",
                    "format": "text",
                    "console": True,
                    "pii_redaction": False,
                },
            }
        )
        assert config.service_name == "dict-service"
        assert config.log_level == "WARNING"
        assert config.log_format == "text"
        assert config.pii_redaction is False

    def test_config_defaults(self) -> None:
        config = LogConfig()
        assert config.service_name == "unknown"
        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.console_output is True

    def test_setup_with_none_uses_defaults(self) -> None:
        setup_logging(None)
        logger = get_logger("default.test")
        assert isinstance(logger, AppLogger)

    def test_level_overrides_applied(self, tmp_path: Path) -> None:
        import logging

        setup_logging(
            {
                "service_name": "override-service",
                "log": {
                    "level": "DEBUG",
                    "levels": {"sqlalchemy.engine": "WARNING"},
                    "console": False,
                },
            }
        )

        sa_logger = logging.getLogger("sqlalchemy.engine")
        assert sa_logger.level == logging.WARNING
