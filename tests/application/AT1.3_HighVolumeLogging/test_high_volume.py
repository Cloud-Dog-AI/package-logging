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

"""AT1.3: High Volume Logging — performance under load tests."""

from __future__ import annotations

import gzip
import json
import time
from pathlib import Path

from cloud_dog_logging import setup_logging, get_logger
from cloud_dog_logging.correlation import set_correlation_id


def _read_text_any(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return stream.read()
    return path.read_text(encoding="utf-8")


class TestHighVolumeLogging:
    """Test suite for high-volume logging performance."""

    def test_10000_app_entries_under_5_seconds(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "perf-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        set_correlation_id("perf-001")

        logger = get_logger("test.perf")
        start = time.monotonic()
        for i in range(10000):
            logger.info(f"Performance entry {i:05d}")
        elapsed = time.monotonic() - start

        assert elapsed < 5.0, f"10,000 entries took {elapsed:.2f}s (limit: 5s)"

    def test_logging_overhead_under_1ms(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "overhead-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        set_correlation_id("perf-002")

        logger = get_logger("test.overhead")

        # Warm up
        for _ in range(100):
            logger.info("Warmup")

        # Measure
        iterations = 1000
        start = time.monotonic()
        for i in range(iterations):
            logger.info(f"Overhead test {i}")
        elapsed = time.monotonic() - start

        avg_ms = (elapsed / iterations) * 1000
        assert avg_ms < 1.0, f"Average overhead {avg_ms:.3f}ms (limit: 1ms)"

    def test_no_entries_lost_under_volume(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "noloss-test",
                "log": {
                    "level": "DEBUG",
                    "app_log": app_log,
                    "console": False,
                    "rotation_max_bytes": 50000,
                    "rotation_backup_count": 100,
                },
            }
        )
        set_correlation_id("perf-003")

        logger = get_logger("test.noloss")
        total = 10000
        for i in range(total):
            logger.info(f"Loss test {i:05d}")

        # Count entries across all rotated files
        total_lines = 0
        for f in sorted(tmp_path.glob("app.log*")):
            if f.suffix == ".gz" and f.with_suffix("").exists():
                # Compression keeps a mirror copy; avoid double counting.
                continue
            content = _read_text_any(f)
            for line in content.strip().splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if payload.get("logger") == "test.noloss":
                    total_lines += 1

        assert total_lines == total, f"Expected {total} entries, found {total_lines}"

    def test_rotation_handles_volume(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "rot-vol-test",
                "log": {
                    "level": "DEBUG",
                    "app_log": app_log,
                    "console": False,
                    "rotation_max_bytes": 10000,
                    "rotation_backup_count": 50,
                },
            }
        )
        set_correlation_id("perf-004")

        logger = get_logger("test.rotvol")
        for i in range(5000):
            logger.info(f"Rotation volume {i:05d}")

        # Should have created multiple rotated files
        files = list(tmp_path.glob("app.log*"))
        assert len(files) > 1, "Expected rotation to create backup files"
