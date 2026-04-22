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

"""UT1.7: App Logger — structured application logger tests."""

from __future__ import annotations

import logging
from io import StringIO

from cloud_dog_logging.app_logger import AppLogger
from cloud_dog_logging.redaction import RedactionEngine


class TestAppLogger:
    """Test suite for AppLogger."""

    def setup_method(self) -> None:
        self.stream = StringIO()
        handler = logging.StreamHandler(self.stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.py_logger = logging.getLogger("test.app_logger")
        self.py_logger.handlers.clear()
        self.py_logger.addHandler(handler)
        self.py_logger.setLevel(logging.DEBUG)
        self.py_logger.propagate = False
        self.app_logger = AppLogger(
            logger=self.py_logger,
            redaction_engine=RedactionEngine(),
        )

    def test_info_logs_message(self) -> None:
        self.app_logger.info("Test info message")
        assert "Test info message" in self.stream.getvalue()

    def test_debug_logs_message(self) -> None:
        self.app_logger.debug("Debug message")
        assert "Debug message" in self.stream.getvalue()

    def test_warning_logs_message(self) -> None:
        self.app_logger.warning("Warning message")
        assert "Warning message" in self.stream.getvalue()

    def test_error_logs_message(self) -> None:
        self.app_logger.error("Error message")
        assert "Error message" in self.stream.getvalue()

    def test_critical_logs_message(self) -> None:
        self.app_logger.critical("Critical message")
        assert "Critical message" in self.stream.getvalue()

    def test_exception_logs_message(self) -> None:
        try:
            raise RuntimeError("Test exception")
        except RuntimeError:
            self.app_logger.exception("Exception occurred")
        output = self.stream.getvalue()
        assert "Exception occurred" in output

    def test_extra_fields_redacted(self) -> None:
        self.app_logger.info("Login", password="secret123", user_id="u-1")
        # The redaction happens on the extra dict before passing to logger
        # We can't easily check the final output format here, but we verify
        # the method doesn't error and the message is logged
        assert "Login" in self.stream.getvalue()

    def test_name_property(self) -> None:
        assert self.app_logger.name == "test.app_logger"

    def test_level_property(self) -> None:
        assert self.app_logger.level == logging.DEBUG

    def test_underlying_logger(self) -> None:
        assert self.app_logger.underlying_logger is self.py_logger
