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

# cloud_dog_logging.sinks — Fan-out audit sink
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: FanOutSink dispatching audit events to multiple sinks.
# Related requirements: FR1.18
# Related architecture: CC1.11

"""Fan-out sink implementation for audit events."""

from __future__ import annotations

import logging

from cloud_dog_logging.audit_schema import AuditEvent
from cloud_dog_logging.sinks.base import AuditSink

_LOGGER = logging.getLogger("cloud_dog_logging.sinks.fan_out")


class FanOutSink:
    """Dispatch each event to multiple sinks."""

    def __init__(self, sinks: list[AuditSink]) -> None:
        if not sinks:
            raise ValueError("FanOutSink requires at least one sink")
        self._sinks = list(sinks)

    def emit(self, event: AuditEvent) -> None:
        """Handle emit."""
        for sink in self._sinks:
            try:
                sink.emit(event)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Audit sink emit failed: %s", exc, extra={"sink": sink.__class__.__name__})

    def flush(self) -> None:
        """Handle flush."""
        for sink in self._sinks:
            try:
                sink.flush()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Audit sink flush failed: %s", exc, extra={"sink": sink.__class__.__name__})

    def close(self) -> None:
        """Handle close."""
        for sink in self._sinks:
            try:
                sink.close()
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Audit sink close failed: %s", exc, extra={"sink": sink.__class__.__name__})
