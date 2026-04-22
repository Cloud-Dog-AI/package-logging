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

"""UT1.2: Text Formatter — human-readable output tests."""

from __future__ import annotations

import logging

from cloud_dog_logging.formatters.text_formatter import TextFormatter
from cloud_dog_logging.correlation import set_correlation_id, set_service_name


class TestTextFormatter:
    """Test suite for TextFormatter."""

    def setup_method(self) -> None:
        set_service_name("test-service")
        set_correlation_id("abcdef123456")
        self.formatter = TextFormatter(service_name="test-service")
        self.logger = logging.getLogger("test.text_formatter")

    def test_output_contains_timestamp(self) -> None:
        record = self.logger.makeRecord("test", logging.INFO, "f", 1, "Msg", (), None)
        output = self.formatter.format(record)
        assert "[" in output and "T" in output and "Z" in output

    def test_output_contains_level(self) -> None:
        record = self.logger.makeRecord("test", logging.WARNING, "f", 1, "Msg", (), None)
        output = self.formatter.format(record)
        assert "WARNING" in output

    def test_output_contains_service_name(self) -> None:
        record = self.logger.makeRecord("test", logging.INFO, "f", 1, "Msg", (), None)
        output = self.formatter.format(record)
        assert "test-service" in output

    def test_output_contains_correlation_id(self) -> None:
        record = self.logger.makeRecord("test", logging.INFO, "f", 1, "Msg", (), None)
        output = self.formatter.format(record)
        assert "abcdef123456" in output

    def test_output_contains_message(self) -> None:
        record = self.logger.makeRecord("test", logging.INFO, "f", 1, "Hello world", (), None)
        output = self.formatter.format(record)
        assert "Hello world" in output

    def test_output_contains_logger_name(self) -> None:
        record = self.logger.makeRecord("my.module", logging.INFO, "f", 1, "Msg", (), None)
        output = self.formatter.format(record)
        assert "my.module" in output

    def test_correlation_disabled(self) -> None:
        formatter = TextFormatter(include_correlation=False)
        record = self.logger.makeRecord("test", logging.INFO, "f", 1, "Msg", (), None)
        output = formatter.format(record)
        assert "abcdef123456" not in output

    def test_exception_included(self) -> None:
        try:
            raise RuntimeError("Test error")
        except RuntimeError:
            import sys

            exc_info = sys.exc_info()
        record = self.logger.makeRecord("test", logging.ERROR, "f", 1, "Err", (), exc_info)
        output = self.formatter.format(record)
        assert "RuntimeError" in output
        assert "Test error" in output
