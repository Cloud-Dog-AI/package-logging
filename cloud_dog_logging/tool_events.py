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

# cloud_dog_logging — Tool event helper
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Convenience helper for standardised tool_call audit events.
# Related requirements: FR1.20
# Related architecture: CC1.13

"""Convenience helper for tool/MCP audit events."""

from __future__ import annotations

from typing import Any

from cloud_dog_logging.audit_schema import Actor, AuditEvent
from cloud_dog_logging.correlation import get_correlation_id, get_service_name


def log_tool_event(
    tool: str,
    profile: str | None = None,
    duration_ms: int | None = None,
    paths: list[str] | None = None,
    outcome: str = "success",
    **details: Any,
) -> None:
    """Emit a standard `tool_call` audit event."""
    from cloud_dog_logging import get_audit_logger

    service = get_service_name()
    actor = Actor(type="service", id=service)
    payload: dict[str, Any] = {"tool": tool}
    if profile is not None:
        payload["profile"] = profile
    if paths is not None:
        payload["paths"] = list(paths)
    payload.update(details)

    event = AuditEvent(
        event_type="tool_call",
        actor=actor,
        action="execute",
        outcome=outcome,
        correlation_id=get_correlation_id(),
        service=service,
        details=payload,
        duration_ms=duration_ms,
    )
    get_audit_logger().emit(event)
