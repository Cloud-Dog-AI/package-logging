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

"""ST1.6: Rotation No Loss — verify no entries lost during rotation."""

from __future__ import annotations

import logging
from pathlib import Path

from cloud_dog_logging.handlers.rotating_file import ConfigurableRotatingHandler
from cloud_dog_logging.formatters.json_formatter import JSONFormatter
from cloud_dog_logging.correlation import set_correlation_id


class TestRotationNoLoss:
    """Test suite verifying no log entries lost during rotation."""

    def test_10000_entries_all_preserved(self, tmp_path: Path) -> None:
        """Write 10,000 entries, trigger rotation, count total across files."""
        log_file = str(tmp_path / "noloss.log")
        handler = ConfigurableRotatingHandler(filename=log_file, max_bytes=500000, backup_count=50)
        handler.setFormatter(JSONFormatter(service_name="noloss-test"))
        set_correlation_id("noloss-001")

        logger = logging.getLogger("test.rotation.noloss")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        total_entries = 10000
        for i in range(total_entries):
            logger.info(f"Entry {i:05d}")

        handler.close()

        # Count total lines across all log files
        total_lines = 0
        for f in sorted(tmp_path.glob("noloss.log*")):
            content = f.read_text()
            lines = [line for line in content.strip().splitlines() if line.strip()]
            total_lines += len(lines)

        assert total_lines == total_entries, f"Expected {total_entries} entries, found {total_lines}"

    def test_rotation_mid_stream_preserves_all(self, tmp_path: Path) -> None:
        """Smaller test: 500 entries with tiny max_bytes to force many rotations."""
        log_file = str(tmp_path / "midstream.log")
        # Increased backup count to accommodate larger JSON records after AU-3 field expansion.
        handler = ConfigurableRotatingHandler(filename=log_file, max_bytes=1000, backup_count=300)
        handler.setFormatter(JSONFormatter(service_name="midstream-test"))
        set_correlation_id("noloss-002")

        logger = logging.getLogger("test.rotation.midstream")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        total_entries = 500
        for i in range(total_entries):
            logger.info(f"Mid {i:04d}")

        handler.close()

        total_lines = 0
        for f in sorted(tmp_path.glob("midstream.log*")):
            content = f.read_text()
            lines = [line for line in content.strip().splitlines() if line.strip()]
            total_lines += len(lines)

        assert total_lines == total_entries
