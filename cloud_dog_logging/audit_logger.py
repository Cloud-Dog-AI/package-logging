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

# cloud_dog_logging — Audit logger (append-only, typed events)
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Typed audit event logger with mandatory schema validation.
#   Supports pluggable sinks and optional signing hooks.
# Related requirements: FR1.3, FR1.10, FR1.13, FR1.14, FR1.18, FR1.19, CS1.1, CS1.2
# Related architecture: CC1.2, CC1.11, CC1.12

"""Audit logger with typed event helpers for cloud_dog_logging."""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import replace
from typing import Any

from cloud_dog_logging.audit_schema import Actor, AuditEvent, Target
from cloud_dog_logging.correlation import (
    get_correlation_id,
    get_environment,
    get_service_instance,
    get_service_name,
)
from cloud_dog_logging.redaction import RedactionEngine
from cloud_dog_logging.signing import AuditSigner
from cloud_dog_logging.sinks.base import AuditSink
from cloud_dog_logging.sinks.file_sink import FileSink


class AuditLogger:
    """Append-only audit event logger with typed helper methods."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        redaction_engine: RedactionEngine | None = None,
        service_name: str | None = None,
        sink: AuditSink | None = None,
        signer: AuditSigner | None = None,
    ) -> None:
        explicit_logger = logger
        self._logger = logger or logging.getLogger("cloud_dog_logging.audit")
        self._redaction = redaction_engine or RedactionEngine()
        self._service_name = service_name
        self._signer = signer
        if sink is None:
            if explicit_logger is None:
                sink = FileSink("logs/audit.log.jsonl")
            else:
                sink = _LoggerSinkAdapter(self._logger)
        self._sink = sink
        self._validate_sink(self._sink)
        self._event_count: int = 0
        self._last_event_timestamp: str | None = None
        self._audit_sink_healthy: bool = True

    def emit(self, event: AuditEvent) -> None:
        """Emit a raw audit event via the configured sink."""
        persisted = self._redact_event(event)
        if self._signer is not None:
            persisted = self._signer.pre_persist(persisted)

        self._emit_with_fallback(persisted)

        if self._signer is not None:
            self._signer.post_persist(persisted)

        self._event_count += 1
        self._last_event_timestamp = persisted.timestamp

    def flush(self) -> None:
        """Flush sink state."""
        self._sink.flush()

    def close(self) -> None:
        """Close sink resources."""
        self._sink.close()

    def _redact_event(self, event: AuditEvent) -> AuditEvent:
        if event.details is None:
            return event
        return replace(event, details=self._redaction.redact(event.details))

    @staticmethod
    def _validate_sink(sink: AuditSink) -> None:
        required = ("emit", "flush", "close")
        for method in required:
            fn = getattr(sink, method, None)
            if not callable(fn):
                raise TypeError(f"Invalid audit sink: missing callable '{method}'")

    def _emit_with_fallback(self, event: AuditEvent) -> None:
        """Emit to sink with fallback handling for audit sink failures."""
        try:
            self._sink.emit(event)
            self._audit_sink_healthy = True
            return
        except Exception as exc:
            self._audit_sink_healthy = False
            logging.getLogger(__name__).critical(
                "audit_sink_failure",
                extra={"error": str(exc), "service": event.service},
            )

        try:
            sys.stderr.write(json.dumps(event.to_dict(), default=str, ensure_ascii=False) + "\n")
            sys.stderr.flush()
        except Exception:
            pass

    def _build_event(
        self,
        event_type: str,
        actor: Actor,
        action: str,
        outcome: str,
        target: Target | None = None,
        duration_ms: int | None = None,
        severity: str = "INFO",
        **details: Any,
    ) -> AuditEvent:
        service = self._service_name or get_service_name()
        correlation_id = get_correlation_id()
        effective_severity = severity
        if severity == "INFO" and outcome in {"failure", "error", "denied"}:
            effective_severity = "ERROR"
        return AuditEvent(
            event_type=event_type,
            actor=actor,
            action=action,
            outcome=outcome,
            correlation_id=correlation_id,
            service=service,
            service_instance=get_service_instance(),
            environment=get_environment(),
            severity=effective_severity,
            target=target,
            details=details if details else None,
            duration_ms=duration_ms,
        )

    def log_login(self, actor: Actor, outcome: str, **details: Any) -> None:
        """Handle log login."""
        event = self._build_event(
            event_type="user.login",
            actor=actor,
            action="login",
            outcome=outcome,
            **details,
        )
        self.emit(event)

    def log_crud(
        self,
        actor: Actor,
        action: str,
        target: Target,
        outcome: str,
        **details: Any,
    ) -> None:
        """Handle log crud."""
        event = self._build_event(
            event_type=f"{target.type}.{action}",
            actor=actor,
            action=action,
            outcome=outcome,
            target=target,
            **details,
        )
        self.emit(event)

    def log_config_change(
        self,
        actor: Actor,
        diff_summary: dict[str, Any],
        outcome: str,
        **details: Any,
    ) -> None:
        """Handle log config change."""
        all_details = {"diff_summary": diff_summary, **details}
        event = self._build_event(
            event_type="config.change",
            actor=actor,
            action="update",
            outcome=outcome,
            **all_details,
        )
        self.emit(event)

    def log_tool_call(
        self,
        actor: Actor,
        tool: str,
        params: dict[str, Any],
        outcome: str,
        duration_ms: int,
        **details: Any,
    ) -> None:
        """Handle log tool call."""
        all_details = {"tool": tool, "params": params, **details}
        event = self._build_event(
            event_type="tool.call",
            actor=actor,
            action="execute",
            outcome=outcome,
            duration_ms=duration_ms,
            **all_details,
        )
        self.emit(event)

    def log_security(
        self,
        actor: Actor,
        action: str,
        target: Target,
        outcome: str,
        **details: Any,
    ) -> None:
        """Handle log security."""
        event = self._build_event(
            event_type=f"security.{action}",
            actor=actor,
            action=action,
            outcome=outcome,
            target=target,
            **details,
        )
        self.emit(event)

    def log_privileged(
        self,
        actor: Actor,
        action: str,
        target: Target,
        outcome: str,
        command_text: str | None = None,
        prior_value: Any | None = None,
        new_value: Any | None = None,
        **details: Any,
    ) -> None:
        """AU-3(1) enhanced audit event for privileged operations."""
        enriched: dict[str, Any] = dict(details)
        if command_text is not None:
            enriched["command_text"] = command_text
        if prior_value is not None:
            enriched["prior_value"] = prior_value
        if new_value is not None:
            enriched["new_value"] = new_value
        event = self._build_event(
            event_type=f"admin.{action}",
            actor=actor,
            action=action,
            outcome=outcome,
            target=target,
            severity="WARNING" if outcome in {"success", "partial"} else "ERROR",
            **enriched,
        )
        self.emit(event)

    @property
    def event_count(self) -> int:
        """Return total audit events emitted since startup."""
        return self._event_count

    @property
    def last_event_timestamp(self) -> str | None:
        """Return the timestamp of the last emitted event."""
        return self._last_event_timestamp

    @property
    def audit_sink_healthy(self) -> bool:
        """Return audit sink health state."""
        return self._audit_sink_healthy


class _LoggerSinkAdapter:
    """Adapter sink that preserves legacy logger-based audit output."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def emit(self, event: AuditEvent) -> None:
        """Handle emit."""
        self._logger.info(json.dumps(event.to_dict(), default=str, ensure_ascii=False))

    def flush(self) -> None:
        """Handle flush."""
        for handler in self._logger.handlers:
            flush = getattr(handler, "flush", None)
            if callable(flush):
                flush()

    def close(self) -> None:
        """Handle close."""
        for handler in self._logger.handlers:
            close = getattr(handler, "close", None)
            if callable(close):
                close()
