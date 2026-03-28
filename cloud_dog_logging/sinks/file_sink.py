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

# cloud_dog_logging.sinks — File-backed audit sink
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: FileSink implementation writing append-only JSON Lines audit
#   events.
# Related requirements: FR1.18, FR1.14, FR1.27
# Related architecture: CC1.11

"""File sink implementation for audit events."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Callable

from cloud_dog_logging.audit_schema import AuditEvent
from cloud_dog_logging.handlers.rotating_file import ConfigurableRotatingHandler


class FileSink:
    """Append-only JSONL sink for audit events."""

    def __init__(
        self,
        path: str,
        max_bytes: int = 10_485_760,
        backup_count: int = 5,
        rotation_mode: str = "size",
        when: str = "midnight",
        interval: int = 1,
        compress: bool = True,
        on_rotate: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._handler = ConfigurableRotatingHandler(
            filename=str(self._path),
            max_bytes=max_bytes,
            backup_count=backup_count,
            append_only=True,
            rotation_mode=rotation_mode,
            when=when,
            interval=interval,
            compress=compress,
            stream_name="audit",
            on_rotate=on_rotate,
        )
        self._handler.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, event: AuditEvent) -> None:
        """Handle emit."""
        payload = json.dumps(event.to_dict(), default=str, ensure_ascii=False)
        record = logging.LogRecord(
            name="cloud_dog_logging.audit.sink",
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg=payload,
            args=(),
            exc_info=None,
        )
        with self._lock:
            self._handler.emit(record)

    def flush(self) -> None:
        """Handle flush."""
        with self._lock:
            self._handler.flush()

    def close(self) -> None:
        """Handle close."""
        with self._lock:
            self._handler.flush()
            self._handler.close()
