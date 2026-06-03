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

# cloud_dog_logging — Audit sink batching wrapper
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: BatchingSink wrapper adding batch size and flush interval
#   semantics to any audit sink.
# Related requirements: FR1.23
# Related architecture: CC1.16

"""Batching wrapper for audit sinks."""

from __future__ import annotations

import threading
import time

from cloud_dog_logging.audit_schema import AuditEvent
from cloud_dog_logging.sinks.base import AuditSink


class BatchingSink:
    """Wrap an audit sink with configurable batch buffering."""

    def __init__(self, sink: AuditSink, batch_size: int = 100, flush_interval_s: float = 5.0) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        if flush_interval_s <= 0:
            raise ValueError("flush_interval_s must be > 0")
        self._sink = sink
        self._batch_size = batch_size
        self._flush_interval_s = flush_interval_s
        self._buffer: list[AuditEvent] = []
        self._lock = threading.Lock()
        self._last_flush_monotonic = time.monotonic()

    def emit(self, event: AuditEvent) -> None:
        """Handle emit."""
        with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self._batch_size or self._flush_interval_elapsed():
                self._flush_locked()

    def flush(self) -> None:
        """Handle flush."""
        with self._lock:
            self._flush_locked()
            self._sink.flush()

    def close(self) -> None:
        """Handle close."""
        with self._lock:
            self._flush_locked()
            self._sink.close()

    def _flush_interval_elapsed(self) -> bool:
        return (time.monotonic() - self._last_flush_monotonic) >= self._flush_interval_s

    def _flush_locked(self) -> None:
        if not self._buffer:
            return
        batch = list(self._buffer)
        self._buffer.clear()

        emit_batch = getattr(self._sink, "emit_batch", None)
        if callable(emit_batch):
            emit_batch(batch)
        else:
            for event in batch:
                self._sink.emit(event)

        self._sink.flush()
        self._last_flush_monotonic = time.monotonic()
