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

# cloud_dog_logging — Audit event schema and models
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Mandatory audit event schema with Actor, Target, and AuditEvent
#   dataclasses. All audit events are validated against this schema before writing.
# Related requirements: FR1.3
# Related architecture: CC1.3

"""Audit event schema and data models for cloud_dog_logging."""

from __future__ import annotations

import os
import re
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

VALID_OUTCOMES = frozenset({"success", "failure", "error", "denied", "partial"})
VALID_ACTOR_TYPES = frozenset({"user", "service", "system"})
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


@dataclass(frozen=True)
class Actor:
    """Represents the entity performing an action.

    Attributes:
        type: The actor type — one of ``user``, ``service``, or ``system``.
        id: A stable identifier for the actor.
        roles: Optional list of roles held by the actor.

    Related tests: UT1.5_AuditSchema
    """

    type: str
    id: str
    roles: list[str] | None = None
    ip: str | None = None
    user_agent: str | None = None
    account_id: str | None = None
    process_id: str | None = None
    device_id: str | None = None

    def __post_init__(self) -> None:
        if self.type not in VALID_ACTOR_TYPES:
            raise ValueError(f"Actor type must be one of {sorted(VALID_ACTOR_TYPES)}, got '{self.type}'")
        if not self.id:
            raise ValueError("Actor id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary, omitting None values."""
        result: dict[str, Any] = {
            "type": self.type,
            "id": self.id,
            "roles": list(self.roles or []),
            "ip": self.ip or "unknown",
        }
        if self.user_agent is not None:
            result["user_agent"] = self.user_agent
        if self.account_id is not None:
            result["account_id"] = self.account_id
        if self.process_id is not None:
            result["process_id"] = self.process_id
        if self.device_id is not None:
            result["device_id"] = self.device_id
        return result


@dataclass(frozen=True)
class Target:
    """Represents the entity being acted upon.

    Attributes:
        type: The target type — e.g. ``user``, ``session``, ``config``, ``api_key``.
        id: A stable identifier for the target entity.

    Related tests: UT1.5_AuditSchema
    """

    type: str
    id: str
    name: str | None = None

    def __post_init__(self) -> None:
        if not self.type:
            raise ValueError("Target type must not be empty")
        if not self.id:
            raise ValueError("Target id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary."""
        result: dict[str, Any] = {"type": self.type, "id": self.id}
        if self.name is not None:
            result["name"] = self.name
        return result


@dataclass
class AuditEvent:
    """Represents a single audit event.

    All required fields are enforced at construction. The timestamp is
    generated automatically in ISO 8601 UTC format if not provided.

    Attributes:
        event_type: The event type, e.g. ``user.login``, ``config.reload``.
        actor: The entity performing the action.
        action: The action performed, e.g. ``create``, ``update``, ``login``.
        outcome: The result — one of ``success``, ``failure``, or ``error``.
        correlation_id: The request/trace correlation identifier.
        service: The originating service name.
        timestamp: ISO 8601 UTC timestamp. Auto-generated if not provided.
        target: Optional target entity.
        details: Optional additional context dictionary (no secrets).
        duration_ms: Optional operation duration in milliseconds.

    Related requirements: FR1.3
    Related tests: UT1.5_AuditSchema
    """

    event_type: str
    actor: Actor
    action: str
    outcome: str
    correlation_id: str
    service: str
    trace_id: str = ""
    request_id: str = ""
    service_instance: str = field(default_factory=socket.gethostname)
    component: str = ""
    source_host: str = field(default_factory=socket.gethostname)
    source_process: str = field(default_factory=lambda: str(os.getpid()))
    source_application: str = ""
    source_address: str | None = None
    destination_address: str | None = None
    process_id: str = field(default_factory=lambda: str(os.getpid()))
    environment: str = "unknown"
    severity: str = "INFO"
    timestamp: str = field(default="")
    target: Target | None = None
    details: dict[str, Any] | None = None
    affected_files: list[str] | None = None
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        if not TIMESTAMP_RE.match(self.timestamp):
            raise ValueError("timestamp must be UTC ISO 8601 with milliseconds, e.g. 2026-01-01T00:00:00.000Z")
        if self.outcome not in VALID_OUTCOMES:
            raise ValueError(f"Outcome must be one of {sorted(VALID_OUTCOMES)}, got '{self.outcome}'")
        if not self.event_type:
            raise ValueError("event_type must not be empty")
        if not self.action:
            raise ValueError("action must not be empty")
        if not self.correlation_id:
            raise ValueError("correlation_id must not be empty")
        if not self.trace_id:
            self.trace_id = self.correlation_id
        if not self.request_id:
            self.request_id = self.correlation_id
        if not self.service:
            raise ValueError("service must not be empty")
        if not self.service_instance:
            raise ValueError("service_instance must not be empty")
        if not self.component:
            self.component = self.service
        if not self.source_host:
            self.source_host = self.service_instance
        if not self.source_process:
            self.source_process = str(os.getpid())
        if not self.source_application:
            self.source_application = self.service
        if not self.process_id:
            self.process_id = self.source_process
        if not self.environment:
            raise ValueError("environment must not be empty")
        if not self.severity:
            raise ValueError("severity must not be empty")

    def to_dict(self) -> dict[str, Any]:
        """Convert the event to a flat dictionary suitable for JSON serialisation.

        Returns:
            A dictionary with all fields. None values are omitted.

        Related tests: UT1.5_AuditSchema
        """
        result: dict[str, Any] = {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor.to_dict(),
            "action": self.action,
            "outcome": self.outcome,
            "severity": self.severity,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "service": self.service,
            "service_instance": self.service_instance,
            "component": self.component,
            "source_host": self.source_host,
            "source_process": self.source_process,
            "source_application": self.source_application,
            "process_id": self.process_id,
            "environment": self.environment,
        }
        if self.source_address is not None:
            result["source_address"] = self.source_address
        if self.destination_address is not None:
            result["destination_address"] = self.destination_address
        if self.target is not None:
            result["target"] = self.target.to_dict()
        if self.details is not None:
            result["details"] = self.details
        if self.affected_files is not None:
            result["affected_files"] = list(self.affected_files)
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        return result
