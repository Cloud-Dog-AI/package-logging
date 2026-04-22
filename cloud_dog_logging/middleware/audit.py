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

# cloud_dog_logging — Audit middleware for FastAPI/Starlette
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: ASGI middleware that emits a NIST-compliant audit event for
#   every HTTP request via AuditLogger.  Captures actor, action, target,
#   outcome, correlation_id, and duration_ms.
# Related requirements: FR1.3, FR1.18, FR1.19, CS1.1
# Related architecture: CC1.2, CC1.8
# Change history:
#   2026-03-31 — W28A-529 — Created.  Fixes missing automatic audit events.

"""ASGI audit middleware — emits one AuditEvent per HTTP request."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from cloud_dog_logging.audit_schema import Actor, Target
from cloud_dog_logging.correlation import get_correlation_id, set_correlation_id

_logger = logging.getLogger("cloud_dog_logging.middleware.audit")

# HTTP methods → semantic action verbs
_METHOD_ACTION_MAP: dict[str, str] = {
    "GET": "read",
    "HEAD": "read",
    "OPTIONS": "read",
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}

# Paths that are high-volume and low-security-value — skip audit
_SKIP_PATHS: frozenset[str] = frozenset({
    "/health",
    "/healthz",
    "/ready",
    "/readyz",
    "/live",
    "/livez",
    "/metrics",
    "/favicon.ico",
})


def _header_value(scope: dict[str, Any], header_name: str) -> str | None:
    """Return a decoded HTTP header value from the ASGI scope."""
    header_key = header_name.lower().encode("latin-1")
    for key, value in scope.get("headers", []):
        if key == header_key:
            try:
                return value.decode("latin-1")
            except Exception:
                return None
    return None


def _normalise_roles(candidate: Any) -> list[str]:
    """Convert role/group containers into stable string role names."""
    if candidate is None:
        return []
    if not isinstance(candidate, (list, tuple, set)):
        candidate = [candidate]
    roles: list[str] = []
    for item in candidate:
        if item is None:
            continue
        if isinstance(item, str):
            role = item
        else:
            role = getattr(item, "name", None) or getattr(item, "id", None) or str(item)
        role_text = str(role).strip()
        if role_text and role_text not in roles:
            roles.append(role_text)
    return roles


class AuditMiddleware:
    """ASGI middleware emitting one audit event per HTTP request.

    Extracts actor identity from request state (set by auth middleware) and
    falls back to ``anonymous`` with the client IP.  The audit event is
    emitted *after* the response status code is known so that the outcome
    is accurate.

    Args:
        app: The ASGI application.
        skip_paths: Paths to exclude from auditing.  Defaults to health/metrics.

    Related tests: IT1.10_AuditMiddleware
    """

    def __init__(
        self,
        app: Any,
        skip_paths: frozenset[str] | None = None,
    ) -> None:
        self.app = app
        self._skip_paths = skip_paths if skip_paths is not None else _SKIP_PATHS

    async def __call__(
        self, scope: dict[str, Any], receive: Callable, send: Callable,
    ) -> None:
        """ASGI interface — intercept HTTP requests and emit audit events."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        if path in self._skip_paths:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        start_time = time.monotonic()
        status_code = 500

        async def send_wrapper(message: dict[str, Any]) -> None:
            """Capture the response status before forwarding the ASGI message."""
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.monotonic() - start_time) * 1000)
            self._emit_audit_event(
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=client_ip,
                scope=scope,
            )

    def _emit_audit_event(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int,
        client_ip: str,
        scope: dict[str, Any],
    ) -> None:
        """Build and emit the audit event via the singleton AuditLogger."""
        try:
            # Lazy import to avoid circular dependency at module load time
            from cloud_dog_logging import get_audit_logger

            audit = get_audit_logger()

            # Determine actor — auth middleware stores user on scope["state"]
            state = scope.get("state", {})
            user = None
            if isinstance(state, dict):
                user = state.get("user")
            elif hasattr(state, "user"):
                user = getattr(state, "user", None)

            if user and isinstance(user, str):
                actor = Actor(
                    type="user",
                    id=user,
                    roles=[],
                    ip=client_ip,
                    user_agent=_header_value(scope, "user-agent"),
                )
            elif user and hasattr(user, "username"):
                roles = _normalise_roles(getattr(user, "roles", None))
                if not roles:
                    roles = _normalise_roles(getattr(user, "groups", None))
                if getattr(user, "is_system_admin", False) and "system_admin" not in roles:
                    roles.append("system_admin")
                actor = Actor(
                    type="user",
                    id=getattr(user, "username", str(user)),
                    roles=roles,
                    ip=client_ip,
                    user_agent=_header_value(scope, "user-agent"),
                )
            else:
                actor = Actor(
                    type="system",
                    id="anonymous",
                    roles=[],
                    ip=client_ip,
                    user_agent=_header_value(scope, "user-agent"),
                )

            action = _METHOD_ACTION_MAP.get(method, "execute")
            outcome = _status_to_outcome(status_code)
            target = Target(type="endpoint", id=path, name=f"{method} {path}")

            event = audit._build_event(
                event_type=f"http.{action}",
                actor=actor,
                action=action,
                outcome=outcome,
                target=target,
                duration_ms=duration_ms,
                status_code=status_code,
                method=method,
                client_ip=client_ip,
            )
            audit.emit(event)
        except Exception as exc:
            _logger.debug("Failed to emit audit event: %s", exc)


def _status_to_outcome(status_code: int) -> str:
    """Map HTTP status code to audit outcome."""
    if status_code < 400:
        return "success"
    if status_code == 401 or status_code == 403:
        return "denied"
    if status_code < 500:
        return "failure"
    return "error"
