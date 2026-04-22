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

# cloud_dog_logging — Structured JSON Lines formatter
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Formats log records as JSON Lines (one JSON object per line).
#   Includes all required fields from FR1.3/FR1.4. Handles exceptions by
#   serialising tracebacks as strings.
# Related requirements: FR1.2, FR1.4
# Related architecture: CC1.6

"""Structured JSON Lines formatter for both log streams."""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from cloud_dog_logging.correlation import (
    get_correlation_id,
    get_environment,
    get_service_instance,
    get_service_name,
)


class JSONFormatter(logging.Formatter):
    """Structured JSON Lines formatter for cloud_dog_logging.

    Produces one JSON object per line with all required fields:
    timestamp, level, logger, message, correlation_id, service, extra.

    Exceptions are serialised as a ``traceback`` string field within the
    JSON object.

    Args:
        service_name: Override service name (otherwise read from context).
        include_extra: Whether to include extra fields. Defaults to True.

    Related tests: UT1.1_JSONFormatter
    """

    def __init__(self, service_name: str | None = None, include_extra: bool = True) -> None:
        super().__init__()
        self._service_name = service_name
        self._include_extra = include_extra
        self._reserved_attrs = frozenset(
            {
                "name",
                "msg",
                "args",
                "created",
                "relativeCreated",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "pathname",
                "filename",
                "module",
                "thread",
                "threadName",
                "process",
                "processName",
                "levelname",
                "levelno",
                "msecs",
                "message",
                "taskName",
            }
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A JSON string representing the log entry (no trailing newline).

        Related tests: UT1.1_JSONFormatter
        """
        # Ensure message is resolved
        record.message = record.getMessage()

        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        service = self._service_name or get_service_name()

        entry: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "correlation_id": get_correlation_id(),
            "service": service,
            "service_instance": get_service_instance(),
            "environment": get_environment(),
        }

        # Include extra fields from the record
        if self._include_extra:
            extra: dict[str, Any] = {}
            for key, value in record.__dict__.items():
                if key not in self._reserved_attrs and not key.startswith("_"):
                    try:
                        json.dumps(value)
                        extra[key] = value
                    except (TypeError, ValueError):
                        extra[key] = str(value)
            if extra:
                entry["extra"] = extra

        # Handle exceptions
        if record.exc_info and record.exc_info[0] is not None:
            entry["traceback"] = "".join(traceback.format_exception(*record.exc_info))

        if record.stack_info:
            entry["stack_info"] = record.stack_info

        return json.dumps(entry, default=str, ensure_ascii=False)
