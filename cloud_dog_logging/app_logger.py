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

# cloud_dog_logging — Application logger (structured JSON, levels)
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Structured application logger with automatic correlation ID
#   injection, secret redaction on extra fields, and configurable formatting.
# Related requirements: FR1.4, FR1.6, FR1.9, FR1.13
# Related architecture: CC1.1

"""Structured application logger for cloud_dog_logging."""

from __future__ import annotations

import logging
import sys
from typing import Any

from cloud_dog_logging.exceptions import format_exception
from cloud_dog_logging.redaction import RedactionEngine


class AppLogger:
    """Structured application logger with redaction support.

    Wraps a standard Python logger and applies secret redaction to all
    extra fields before logging. Automatically includes correlation ID
    via the configured formatter.

    Args:
        logger: The underlying Python logger.
        redaction_engine: Redaction engine for extra fields. If None,
            a default engine is created.

    Related tests: UT1.7_AppLogger
    """

    def __init__(
        self,
        logger: logging.Logger,
        redaction_engine: RedactionEngine | None = None,
    ) -> None:
        self._logger = logger
        self._redaction = redaction_engine or RedactionEngine()

    def _redact_extra(self, extra: dict[str, Any] | None) -> dict[str, Any]:
        """Redact sensitive values from extra fields.

        Args:
            extra: The extra fields dictionary.

        Returns:
            A redacted copy of the extra fields.
        """
        if not extra:
            return {}
        return self._redaction.redact(extra)

    def debug(self, msg: str, **extra: Any) -> None:
        """Log a DEBUG-level message.

        Args:
            msg: The log message.
            **extra: Additional context fields (will be redacted).
        """
        self._logger.debug(msg, extra=self._redact_extra(extra))

    def info(self, msg: str, **extra: Any) -> None:
        """Log an INFO-level message.

        Args:
            msg: The log message.
            **extra: Additional context fields (will be redacted).
        """
        self._logger.info(msg, extra=self._redact_extra(extra))

    def warning(self, msg: str, **extra: Any) -> None:
        """Log a WARNING-level message.

        Args:
            msg: The log message.
            **extra: Additional context fields (will be redacted).
        """
        self._logger.warning(msg, extra=self._redact_extra(extra))

    def error(self, msg: str, **extra: Any) -> None:
        """Log an ERROR-level message.

        Args:
            msg: The log message.
            **extra: Additional context fields (will be redacted).
        """
        self._logger.error(msg, extra=self._redact_extra(extra))

    def critical(self, msg: str, **extra: Any) -> None:
        """Log a CRITICAL-level message.

        Args:
            msg: The log message.
            **extra: Additional context fields (will be redacted).
        """
        self._logger.critical(msg, extra=self._redact_extra(extra))

    def exception(self, msg: str, **extra: Any) -> None:
        """Log an ERROR-level message with exception information.

        Args:
            msg: The log message.
            **extra: Additional context fields (will be redacted).
        """
        _, exc_value, _ = sys.exc_info()
        payload = dict(extra)
        if isinstance(exc_value, BaseException):
            payload["exception"] = format_exception(exc_value)
        self._logger.error(msg, exc_info=True, extra=self._redact_extra(payload))

    @property
    def level(self) -> int:
        """Return the effective log level."""
        return self._logger.getEffectiveLevel()

    @property
    def name(self) -> str:
        """Return the logger name."""
        return self._logger.name

    @property
    def underlying_logger(self) -> logging.Logger:
        """Return the underlying stdlib logger for advanced use."""
        return self._logger
