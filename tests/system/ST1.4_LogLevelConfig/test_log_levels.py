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

"""ST1.4: Log Level Configuration — per-logger level override tests."""

from __future__ import annotations

import logging
from pathlib import Path

from cloud_dog_logging import setup_logging, get_logger
from cloud_dog_logging.correlation import set_correlation_id


class TestLogLevelConfig:
    """Test suite for log level configuration."""

    def test_global_level_from_config(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "level-test",
                "log": {"level": "WARNING", "app_log": app_log, "console": False},
            }
        )
        set_correlation_id("level-001")

        logger = get_logger("test.level.global")
        logger.info("Should not appear")
        logger.warning("Should appear")

        content = Path(app_log).read_text()
        assert "Should not appear" not in content
        assert "Should appear" in content

    def test_per_logger_override(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "override-test",
                "log": {
                    "level": "DEBUG",
                    "app_log": app_log,
                    "console": False,
                    "levels": {"noisy.module": "ERROR"},
                },
            }
        )
        set_correlation_id("level-002")

        # The overridden logger should only show ERROR+
        noisy = logging.getLogger("noisy.module")
        assert noisy.level == logging.ERROR

    def test_default_level_is_info(self) -> None:
        setup_logging({"service_name": "default-level"})
        root = logging.getLogger()
        assert root.level == logging.INFO
