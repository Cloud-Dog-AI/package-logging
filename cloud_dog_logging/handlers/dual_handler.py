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

# cloud_dog_logging — Dual handler (file + stdout simultaneously)
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Composite handler that writes to both a file handler and
#   a stdout handler simultaneously.
# Related requirements: FR1.7
# Related architecture: CC1.7

"""Dual handler — file + stdout simultaneously."""

from __future__ import annotations

import logging


class DualHandler(logging.Handler):
    """Composite handler that writes to both file and stdout.

    Delegates each log record to both a file handler and a stream handler,
    ensuring entries appear in both destinations with consistent formatting.

    Args:
        file_handler: The file handler for persistent log storage.
        stream_handler: The stream handler for stdout/stderr output.

    Related tests: ST1.5_DualDestination
    """

    def __init__(self, file_handler: logging.Handler, stream_handler: logging.Handler) -> None:
        super().__init__()
        self._file_handler = file_handler
        self._stream_handler = stream_handler

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record to both file and stream handlers.

        Args:
            record: The log record to emit.
        """
        self._file_handler.emit(record)
        self._stream_handler.emit(record)

    def setFormatter(self, fmt: logging.Formatter | None) -> None:
        """Set the formatter on both handlers.

        Args:
            fmt: The formatter to apply to both handlers.
        """
        super().setFormatter(fmt)
        self._file_handler.setFormatter(fmt)
        self._stream_handler.setFormatter(fmt)

    def close(self) -> None:
        """Close both handlers."""
        self._file_handler.close()
        self._stream_handler.close()
        super().close()

    @property
    def file_handler(self) -> logging.Handler:
        """Return the file handler."""
        return self._file_handler

    @property
    def stream_handler(self) -> logging.Handler:
        """Return the stream handler."""
        return self._stream_handler
