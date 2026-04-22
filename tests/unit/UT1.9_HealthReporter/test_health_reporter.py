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

"""UT1.9: Health Reporter — log subsystem observability tests."""

from __future__ import annotations

from pathlib import Path

from cloud_dog_logging.health.reporter import LogHealthReporter


class _MockAuditLogger:
    """Mock audit logger for health reporter tests."""

    def __init__(self, event_count: int = 5, last_ts: str | None = "2026-01-01T00:00:00Z") -> None:
        self.event_count = event_count
        self.last_event_timestamp = last_ts


class TestLogHealthReporter:
    """Test suite for LogHealthReporter."""

    def test_status_with_no_files(self) -> None:
        reporter = LogHealthReporter()
        status = reporter.get_status()
        assert status["app_log_size_bytes"] is None
        assert status["audit_log_size_bytes"] is None
        assert status["audit_event_count"] == 0

    def test_status_with_app_log_file(self, tmp_path: Path) -> None:
        log_file = tmp_path / "app.log"
        log_file.write_text("line1\nline2\n")
        reporter = LogHealthReporter(app_log_path=str(log_file))
        status = reporter.get_status()
        assert status["app_log_size_bytes"] == log_file.stat().st_size

    def test_status_with_audit_log_file(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.log.jsonl"
        log_file.write_text('{"event": "test"}\n')
        reporter = LogHealthReporter(audit_log_path=str(log_file))
        status = reporter.get_status()
        assert status["audit_log_size_bytes"] == log_file.stat().st_size

    def test_status_with_audit_logger(self) -> None:
        mock_audit = _MockAuditLogger(event_count=10, last_ts="2026-02-15T12:00:00Z")
        reporter = LogHealthReporter(audit_logger=mock_audit)
        status = reporter.get_status()
        assert status["audit_event_count"] == 10
        assert status["last_audit_event_timestamp"] == "2026-02-15T12:00:00Z"

    def test_rotated_files_counted(self, tmp_path: Path) -> None:
        base = tmp_path / "app.log"
        base.write_text("current\n")
        (tmp_path / "app.log.1").write_text("rotated1\n")
        (tmp_path / "app.log.2").write_text("rotated2\n")
        reporter = LogHealthReporter(app_log_path=str(base))
        status = reporter.get_status()
        assert status["app_log_rotated_files"] == 2

    def test_nonexistent_file_returns_none(self) -> None:
        reporter = LogHealthReporter(app_log_path="/nonexistent/path/app.log")
        status = reporter.get_status()
        assert status["app_log_size_bytes"] is None

    def test_all_status_keys_present(self) -> None:
        reporter = LogHealthReporter()
        status = reporter.get_status()
        expected_keys = {
            "app_log_size_bytes",
            "audit_log_size_bytes",
            "app_log_rotated_files",
            "audit_log_rotated_files",
            "audit_event_count",
            "last_audit_event_timestamp",
            "audit_sink_healthy",
        }
        assert set(status.keys()) == expected_keys
