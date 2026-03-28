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

"""UT1.1: JSON Formatter — structured JSON Lines output tests."""

from __future__ import annotations

import json
import logging

from cloud_dog_logging.formatters.json_formatter import JSONFormatter
from cloud_dog_logging.correlation import set_correlation_id, set_service_name


class TestJSONFormatter:
    """Test suite for JSONFormatter."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        set_service_name("test-service")
        set_correlation_id("test-corr-001")
        self.formatter = JSONFormatter(service_name="test-service")
        self.logger = logging.getLogger("test.json_formatter")
        self.logger.setLevel(logging.DEBUG)

    def test_output_is_valid_json(self) -> None:
        """Each formatted record MUST be valid JSON."""
        record = self.logger.makeRecord("test", logging.INFO, "test.py", 1, "Test message", (), None)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_one_json_per_line(self) -> None:
        """Output MUST be one JSON object per line (no embedded newlines in JSON)."""
        record = self.logger.makeRecord("test", logging.INFO, "test.py", 1, "Line one\nLine two", (), None)
        output = self.formatter.format(record)
        # Should be a single line of valid JSON
        assert "\n" not in output or output.count("\n") == 0
        json.loads(output)

    def test_required_fields_present(self) -> None:
        """All required fields from FR1.4 MUST be present."""
        record = self.logger.makeRecord("test.module", logging.WARNING, "test.py", 1, "Warning msg", (), None)
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert "timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed
        assert "correlation_id" in parsed
        assert "service" in parsed

    def test_level_field_value(self) -> None:
        """Level field MUST contain the log level name."""
        record = self.logger.makeRecord("test", logging.ERROR, "test.py", 1, "Error", (), None)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "ERROR"

    def test_logger_name_field(self) -> None:
        """Logger field MUST contain the logger name."""
        record = self.logger.makeRecord("my.module.name", logging.INFO, "test.py", 1, "Msg", (), None)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert parsed["logger"] == "my.module.name"

    def test_message_field(self) -> None:
        """Message field MUST contain the formatted message."""
        record = self.logger.makeRecord("test", logging.INFO, "test.py", 1, "Hello %s", ("world",), None)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "Hello world"

    def test_correlation_id_from_context(self) -> None:
        """Correlation ID MUST be read from context."""
        set_correlation_id("custom-corr-123")
        record = self.logger.makeRecord("test", logging.INFO, "test.py", 1, "Msg", (), None)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert parsed["correlation_id"] == "custom-corr-123"

    def test_service_name_field(self) -> None:
        """Service field MUST contain the configured service name."""
        record = self.logger.makeRecord("test", logging.INFO, "test.py", 1, "Msg", (), None)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert parsed["service"] == "test-service"

    def test_timestamp_iso8601_utc(self) -> None:
        """Timestamp MUST be in ISO 8601 UTC format."""
        record = self.logger.makeRecord("test", logging.INFO, "test.py", 1, "Msg", (), None)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        ts = parsed["timestamp"]
        assert ts.endswith("Z")
        assert "T" in ts

    def test_extra_fields_included(self) -> None:
        """Extra fields MUST be included in the output."""
        record = self.logger.makeRecord("test", logging.INFO, "test.py", 1, "Msg", (), None)
        record.user_id = "u-123"
        record.action = "login"
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert "extra" in parsed
        assert parsed["extra"]["user_id"] == "u-123"
        assert parsed["extra"]["action"] == "login"

    def test_exception_serialisation(self) -> None:
        """Exception info MUST be serialised as a traceback string."""
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = self.logger.makeRecord("test", logging.ERROR, "test.py", 1, "Error occurred", (), exc_info)
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert "traceback" in parsed
        assert "ValueError" in parsed["traceback"]
        assert "Test error" in parsed["traceback"]

    def test_no_extra_when_disabled(self) -> None:
        """Extra fields SHOULD NOT be included when include_extra=False."""
        formatter = JSONFormatter(include_extra=False)
        record = self.logger.makeRecord("test", logging.INFO, "test.py", 1, "Msg", (), None)
        record.custom_field = "value"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "extra" not in parsed
