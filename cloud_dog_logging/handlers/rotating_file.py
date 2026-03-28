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

# cloud_dog_logging — Size and time-based rotating file handler
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Configurable rotating file handler that combines size-based and
#   time-based rotation with retention policy. Rotation MUST NOT lose entries.
# Related requirements: FR1.7, FR1.8, FR1.27
# Related architecture: CC1.7

"""Size and time-based rotating file handler for cloud_dog_logging."""

from __future__ import annotations

import gzip
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable


class ConfigurableRotatingHandler(RotatingFileHandler):
    """Rotating file handler with size and optional time triggers."""

    def __init__(
        self,
        filename: str,
        max_bytes: int = 10_485_760,
        backup_count: int = 5,
        encoding: str = "utf-8",
        append_only: bool = False,
        rotation_mode: str = "size",
        when: str = "midnight",
        interval: int = 1,
        compress: bool = False,
        stream_name: str = "application",
        on_rotate: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        self._append_only = append_only
        self._rotation_mode = (rotation_mode or "size").lower()
        if self._rotation_mode not in {"size", "time", "both"}:
            self._rotation_mode = "size"
        self._rotation_when = (when or "midnight").lower()
        self._rotation_interval = max(1, int(interval))
        self._rotation_compress = bool(compress)
        self._stream_name = stream_name
        self._on_rotate = on_rotate
        self._next_rollover_ts = self._compute_next_rollover(time.time())
        self._last_rollover_reason = "size"

        super().__init__(
            filename=filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=encoding,
            mode="a",
        )

    def _compute_next_rollover(self, now: float) -> float:
        if self._rotation_when in {"s", "sec", "second", "seconds"}:
            return now + self._rotation_interval
        if self._rotation_when in {"m", "min", "minute", "minutes"}:
            return now + (60 * self._rotation_interval)
        if self._rotation_when in {"h", "hour", "hours"}:
            return now + (3600 * self._rotation_interval)
        if self._rotation_when == "midnight":
            current = time.localtime(now)
            midnight = time.mktime(
                (
                    current.tm_year,
                    current.tm_mon,
                    current.tm_mday,
                    0,
                    0,
                    0,
                    current.tm_wday,
                    current.tm_yday,
                    current.tm_isdst,
                )
            )
            return midnight + (86400 * self._rotation_interval)
        return now + self._rotation_interval

    def _is_time_rollover_due(self) -> bool:
        if self._rotation_mode not in {"time", "both"}:
            return False
        return time.time() >= self._next_rollover_ts

    def _is_size_rollover_due(self, record: logging.LogRecord) -> bool:
        if self._rotation_mode not in {"size", "both"}:
            return False
        if self.maxBytes <= 0:
            return False

        if self.stream is None:
            self.stream = self._open()

        self.stream.flush()

        try:
            self.stream.seek(0, 2)
            current_size = self.stream.tell()
        except OSError:
            current_size = os.path.getsize(self.baseFilename) if os.path.exists(self.baseFilename) else 0

        msg = self.format(record)
        projected = current_size + len(msg.encode(self.encoding or "utf-8")) + 1
        return projected >= self.maxBytes

    def shouldRollover(self, record: logging.LogRecord) -> int:  # noqa: N802 - stdlib API compatibility
        """Handle should rollover."""
        size_due = self._is_size_rollover_due(record)
        time_due = self._is_time_rollover_due()
        if not (size_due or time_due):
            return 0

        if size_due and time_due:
            self._last_rollover_reason = "both"
        elif time_due:
            self._last_rollover_reason = "time"
        else:
            self._last_rollover_reason = "size"
        return 1

    def doRollover(self) -> None:  # noqa: N802 - stdlib API compatibility
        """Handle do rollover."""
        old_file = self.baseFilename
        old_size = os.path.getsize(old_file) if os.path.exists(old_file) else 0
        super().doRollover()

        rotated_file = f"{old_file}.1"
        if self._rotation_compress and os.path.exists(rotated_file):
            gz_path = f"{rotated_file}.gz"
            try:
                with open(rotated_file, "rb") as source, gzip.open(gz_path, "wb") as destination:
                    destination.writelines(source)
            except OSError:
                pass

        self._next_rollover_ts = self._compute_next_rollover(time.time())

        payload: dict[str, object] = {
            "event": "log_rotation",
            "stream": self._stream_name,
            "old_file": old_file,
            "new_file": rotated_file,
            "reason": self._last_rollover_reason,
            "file_size_bytes": old_size,
        }
        logging.getLogger("cloud_dog_logging.rotation").info("log_rotation", extra=payload)

        if self._on_rotate is not None:
            try:
                self._on_rotate(payload)
            except Exception:
                logging.getLogger("cloud_dog_logging.rotation").exception("rotation_callback_failed")

    def emit(self, record: logging.LogRecord) -> None:
        """Handle emit."""
        try:
            if self.shouldRollover(record):
                self.doRollover()
            logging.FileHandler.emit(self, record)
            if self.stream:
                self.stream.flush()
        except Exception:
            self.handleError(record)
