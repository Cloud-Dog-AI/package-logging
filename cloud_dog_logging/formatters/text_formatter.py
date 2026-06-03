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

# cloud_dog_logging — Human-readable text formatter
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Human-readable log formatter for development mode.
#   Produces coloured, structured text output for terminal use.
# Related requirements: FR1.2
# Related architecture: CC1.6

"""Human-readable text formatter for development mode."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from cloud_dog_logging.correlation import get_correlation_id, get_service_name


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for cloud_dog_logging.

    Produces structured text output suitable for terminal/development use.
    Format: ``[TIMESTAMP] LEVEL service correlation_id logger — message``

    Args:
        service_name: Override service name (otherwise read from context).
        include_correlation: Whether to include correlation ID. Defaults to True.

    Related tests: UT1.2_TextFormatter
    """

    def __init__(self, service_name: str | None = None, include_correlation: bool = True) -> None:
        super().__init__()
        self._service_name = service_name
        self._include_correlation = include_correlation

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as human-readable text.

        Args:
            record: The log record to format.

        Returns:
            A formatted text string.

        Related tests: UT1.2_TextFormatter
        """
        record.message = record.getMessage()

        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        service = self._service_name or get_service_name()
        parts = [f"[{timestamp}]", record.levelname.ljust(8), service]

        if self._include_correlation:
            cid = get_correlation_id()
            parts.append(cid[:12] if cid else "—")

        parts.append(record.name)
        parts.append("—")
        parts.append(record.message)

        result = " ".join(parts)

        if record.exc_info and record.exc_info[0] is not None:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            result = f"{result}\n{record.exc_text}"

        if record.stack_info:
            result = f"{result}\n{record.stack_info}"

        return result
