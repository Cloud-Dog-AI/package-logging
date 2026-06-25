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

"""ST1.5: Dual Destination — file + stdout simultaneous output tests."""

from __future__ import annotations

from pathlib import Path

from cloud_dog_logging import setup_logging, get_logger
from cloud_dog_logging.correlation import set_correlation_id


class TestDualDestination:
    """Test suite for dual destination (file + stdout)."""

    def test_entries_appear_in_file(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "dual-test",
                "log": {
                    "level": "DEBUG",
                    "app_log": app_log,
                    "console": True,
                },
            }
        )
        set_correlation_id("dual-001")

        logger = get_logger("test.dual")
        logger.info("Dual destination test")

        content = Path(app_log).read_text()
        assert "Dual destination test" in content

    def test_file_only_when_console_disabled(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "file-only-test",
                "log": {
                    "level": "DEBUG",
                    "app_log": app_log,
                    "console": False,
                },
            }
        )
        set_correlation_id("dual-002")

        logger = get_logger("test.fileonly")
        logger.info("File only test")

        content = Path(app_log).read_text()
        assert "File only test" in content
