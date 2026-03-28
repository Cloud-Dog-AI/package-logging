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

"""UT1.10: Backward Compatibility — setup_logger() tests."""

from __future__ import annotations

import logging
from pathlib import Path

from cloud_dog_logging.compat import setup_logger


class TestSetupLogger:
    """Test suite for backward-compatible setup_logger()."""

    def test_returns_stdlib_logger(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("test.compat", log_file)
        assert isinstance(logger, logging.Logger)

    def test_logger_name_matches(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("my.module", log_file)
        assert logger.name == "my.module"

    def test_respects_log_level(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("test.level", log_file, log_level="WARNING")
        assert logger.level == logging.WARNING

    def test_json_format(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("test.json", log_file, log_format="json")
        logger.info("Test JSON")
        # Verify file was written
        assert Path(log_file).exists()
        content = Path(log_file).read_text()
        assert "Test JSON" in content

    def test_text_format(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("test.text", log_file, log_format="text")
        logger.info("Test text")
        content = Path(log_file).read_text()
        assert "Test text" in content

    def test_console_true_adds_handler(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("test.console", log_file, console=True)
        # Should have both file and console handlers
        assert len(logger.handlers) == 2

    def test_console_false_file_only(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("test.nocons", log_file, console=False)
        assert len(logger.handlers) == 1

    def test_creates_log_directory(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "subdir" / "test.log")
        logger = setup_logger("test.mkdir", log_file)
        logger.info("Directory test")
        assert Path(log_file).exists()

    def test_no_propagation(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("test.prop", log_file)
        assert logger.propagate is False

    def test_default_level_is_info(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("test.default", log_file)
        assert logger.level == logging.INFO
