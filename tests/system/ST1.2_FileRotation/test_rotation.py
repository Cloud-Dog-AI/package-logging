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

"""ST1.2: File Rotation — size-based rotation tests."""

from __future__ import annotations

from pathlib import Path

from cloud_dog_logging.handlers.rotating_file import ConfigurableRotatingHandler
from cloud_dog_logging.formatters.json_formatter import JSONFormatter
from cloud_dog_logging.correlation import set_correlation_id

import logging


class TestFileRotation:
    """Test suite for file rotation."""

    def test_file_rotated_at_configured_size(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "rotate.log")
        handler = ConfigurableRotatingHandler(filename=log_file, max_bytes=500, backup_count=3)
        handler.setFormatter(JSONFormatter(service_name="test"))
        set_correlation_id("rot-001")

        logger = logging.getLogger("test.rotation.size")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        # Write enough entries to trigger rotation
        for i in range(50):
            logger.info(f"Rotation test entry {i:04d}")

        handler.close()

        # Verify backup files exist
        base = Path(log_file)
        assert base.exists()
        assert (tmp_path / "rotate.log.1").exists()

    def test_backup_count_enforced(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "backup.log")
        handler = ConfigurableRotatingHandler(filename=log_file, max_bytes=200, backup_count=2)
        handler.setFormatter(JSONFormatter(service_name="test"))
        set_correlation_id("rot-002")

        logger = logging.getLogger("test.rotation.backup")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        for i in range(100):
            logger.info(f"Backup count test {i:04d}")

        handler.close()

        # Should have at most backup_count rotated files
        rotated = list(tmp_path.glob("backup.log.*"))
        assert len(rotated) <= 2

    def test_rotation_creates_directory(self, tmp_path: Path) -> None:
        log_file = str(tmp_path / "subdir" / "app.log")
        handler = ConfigurableRotatingHandler(filename=log_file, max_bytes=1000)
        handler.setFormatter(JSONFormatter(service_name="test"))
        set_correlation_id("rot-003")

        logger = logging.getLogger("test.rotation.mkdir")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        logger.info("Directory creation test")
        handler.close()

        assert Path(log_file).exists()
