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

# cloud_dog_logging.sinks — Stdout audit sink
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: StdoutSink implementation writing JSON audit events to stdout.
# Related requirements: FR1.18
# Related architecture: CC1.11

"""Stdout sink implementation for audit events."""

from __future__ import annotations

import json
import sys
import threading
from typing import TextIO

from cloud_dog_logging.audit_schema import AuditEvent


class StdoutSink:
    """Write audit events to stdout as JSON lines."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stdout
        self._lock = threading.Lock()

    def emit(self, event: AuditEvent) -> None:
        """Handle emit."""
        payload = json.dumps(event.to_dict(), default=str, ensure_ascii=False)
        with self._lock:
            self._stream.write(payload + "\n")
            self._stream.flush()

    def flush(self) -> None:
        """Handle flush."""
        with self._lock:
            self._stream.flush()

    def close(self) -> None:
        """Handle close."""
        self.flush()
