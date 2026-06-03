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

# cloud_dog_logging.sinks — Database-backed audit sink
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: DatabaseSink implementation persisting audit events through a
#   repository protocol.
# Related requirements: FR1.18
# Related architecture: CC1.11

"""Database sink implementation for audit events."""

from __future__ import annotations

from cloud_dog_logging.audit_schema import AuditEvent
from cloud_dog_logging.sinks.base import AuditRepository


class DatabaseSink:
    """Persist audit events to a database via repository protocol."""

    def __init__(self, repository: AuditRepository | None = None) -> None:
        if repository is None:
            raise ImportError(
                "DatabaseSink requires a repository implementation. "
                "Provide an object implementing insert_event(event_dict)."
            )
        self._repository = repository

    def emit(self, event: AuditEvent) -> None:
        """Handle emit."""
        self._repository.insert_event(event.to_dict())

    def emit_batch(self, events: list[AuditEvent]) -> None:
        """Emit batch."""
        serialised = [event.to_dict() for event in events]
        insert_many = getattr(self._repository, "insert_events", None)
        if callable(insert_many):
            insert_many(serialised)
            return
        for payload in serialised:
            self._repository.insert_event(payload)

    def flush(self) -> None:
        """Handle flush."""
        flush_fn = getattr(self._repository, "flush", None)
        if callable(flush_fn):
            flush_fn()

    def close(self) -> None:
        """Handle close."""
        close_fn = getattr(self._repository, "close", None)
        if callable(close_fn):
            close_fn()
