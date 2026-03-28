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

# cloud_dog_logging — FastAPI request logging and correlation ID middleware
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: ASGI middleware for FastAPI that extracts or generates correlation
#   IDs, logs request/response details, and adds X-Request-Id to responses.
# Related requirements: FR1.15, FR1.5
# Related architecture: CC1.8

"""FastAPI request logging and correlation ID middleware."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable

from cloud_dog_logging.correlation import (
    set_correlation_id,
    clear_correlation_id,
)


class LoggingMiddleware:
    """FastAPI/Starlette ASGI middleware for request logging and correlation ID.

    On each request:
    1. Extracts or generates correlation ID from ``X-Request-Id`` header.
    2. Sets correlation ID in contextvars for the request scope.
    3. Logs request start (method, path, client IP).
    4. Calls the next middleware/handler.
    5. Logs request end (status code, duration in ms).
    6. Adds ``X-Request-Id`` to response headers.

    Args:
        app: The ASGI application.
        logger: Optional logger instance. Falls back to stdlib logging.
        header_name: The request header to read/write correlation ID.
            Defaults to ``X-Request-Id``.
        redact_headers: Headers whose values should be redacted in logs.
            Defaults to Authorization, X-API-Key, Cookie.

    Related tests: IT1.1_FastAPIMiddleware, IT1.2_CorrelationPropagation,
        IT1.3_RequestResponseLogging
    """

    def __init__(
        self,
        app: Any,
        logger: logging.Logger | None = None,
        header_name: str = "X-Request-Id",
        redact_headers: list[str] | None = None,
    ) -> None:
        self.app = app
        self._logger = logger or logging.getLogger("cloud_dog_logging.middleware")
        self._header_name = header_name.lower()
        self._header_name_original = header_name
        self._redact_headers = {h.lower() for h in (redact_headers or ["Authorization", "X-API-Key", "Cookie"])}

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        """ASGI interface — process HTTP requests.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract headers
        headers = dict(scope.get("headers", []))
        request_id = None
        for key, value in headers.items():
            if key.decode("latin-1").lower() == self._header_name:
                request_id = value.decode("latin-1")
                break

        if not request_id:
            request_id = uuid.uuid4().hex

        set_correlation_id(request_id)

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"").decode("latin-1")
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        self._logger.info(
            "Request started",
            extra={
                "method": method,
                "path": path,
                "query_string": query_string,
                "client_ip": client_ip,
                "request_id": request_id,
            },
        )

        start_time = time.monotonic()
        status_code = 500  # default if we never see a response

        async def send_wrapper(message: dict[str, Any]) -> None:
            """Handle send wrapper."""
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                # Add X-Request-Id to response headers only if not already present
                # (e.g. cloud_dog_api_kit CorrelationMiddleware may have set it).
                response_headers = list(message.get("headers", []))
                header_lower = self._header_name.encode("latin-1")
                already_set = any(
                    k.lower() == header_lower for k, _ in response_headers
                )
                if not already_set:
                    response_headers.append((self._header_name_original.encode("latin-1"), request_id.encode("latin-1")))
                message = {**message, "headers": response_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            self._logger.exception(
                "Request failed with unhandled exception",
                extra={
                    "method": method,
                    "path": path,
                    "request_id": request_id,
                    "client_ip": client_ip,
                },
            )
            raise
        finally:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            self._logger.info(
                "Request completed",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "request_id": request_id,
                },
            )
            clear_correlation_id()
