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

# cloud_dog_logging — Correlation ID context (contextvars)
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Context-local correlation ID using contextvars for async-safe
#   propagation across request boundaries.
# Related requirements: FR1.5, NF1.3, CS1.3
# Related architecture: CC1.4

"""Correlation ID context management using contextvars."""

from __future__ import annotations

import socket
import uuid
from contextvars import ContextVar

_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_service_name_var: ContextVar[str] = ContextVar("service_name", default="unknown")
_service_instance_var: ContextVar[str] = ContextVar("service_instance", default=socket.gethostname())
_environment_var: ContextVar[str] = ContextVar("environment", default="unknown")


def get_correlation_id() -> str:
    """Get current correlation ID, generating a new one if none is set.

    Returns:
        The current correlation ID string (UUID hex format).
    """
    cid = _correlation_id_var.get()
    if cid is None:
        cid = uuid.uuid4().hex
        _correlation_id_var.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """Set correlation ID for the current context.

    Args:
        cid: The correlation ID to set. Must not contain sensitive information.
    """
    _correlation_id_var.set(cid)


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    _correlation_id_var.set(None)


def get_service_name() -> str:
    """Get the current service name.

    Returns:
        The configured service name string.
    """
    return _service_name_var.get()


def set_service_name(name: str) -> None:
    """Set the service name for the current context.

    Args:
        name: The service name to set.
    """
    _service_name_var.set(name)


def get_service_instance() -> str:
    """Get the current service instance identifier."""
    return _service_instance_var.get()


def set_service_instance(instance: str) -> None:
    """Set the service instance identifier for the current context."""
    _service_instance_var.set(instance)


def get_environment() -> str:
    """Get the current execution environment."""
    return _environment_var.get()


def set_environment(environment: str) -> None:
    """Set the execution environment for the current context."""
    _environment_var.set(environment)
