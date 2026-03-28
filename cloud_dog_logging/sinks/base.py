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

# cloud_dog_logging.sinks — Audit sink protocol
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Protocol definitions for pluggable audit persistence sinks.
# Related requirements: FR1.18
# Related architecture: CC1.11

"""Base sink protocols for cloud_dog_logging audit events."""

from __future__ import annotations

from typing import Any, Protocol

from cloud_dog_logging.audit_schema import AuditEvent


class AuditSink(Protocol):
    """Protocol for audit event persistence sinks."""

    def emit(self, event: AuditEvent) -> None:
        """Persist one audit event."""

    def flush(self) -> None:
        """Flush buffered sink state."""

    def close(self) -> None:
        """Close sink resources."""


class AuditRepository(Protocol):
    """Repository protocol used by DatabaseSink."""

    def insert_event(self, event: dict[str, Any]) -> None:
        """Persist one serialised audit event."""

    def insert_events(self, events: list[dict[str, Any]]) -> None:
        """Persist multiple serialised audit events."""
