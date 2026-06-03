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

# cloud_dog_logging — LogRecord factory injection (custom field providers)
#
# Licence: Apache 2.0 — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Provides a public, idempotent API for installing arbitrary
#   per-record fields (e.g. ``server_id``) onto every log record produced via
#   stdlib ``logging`` once a provider is registered. Delivered to close the
#   notification-agent ``logger.py`` wrapper architectural-ceiling stop where
#   the platform package previously did not expose this surface.
# Related requirements: FR1.4, FR1.6, FR1.17
# Related architecture: CC1.6, CC1.9
# Related tests: UT_LogRecordFactory

"""Public API for installing custom log-record fields via the stdlib LogRecord factory.

Usage (replaces bespoke ``logging.setLogRecordFactory(...)`` wrappers in services):

    from cloud_dog_logging import register_log_field_provider
    import socket

    register_log_field_provider("server_id", lambda: socket.gethostname())

After registration every ``logging.LogRecord`` produced by stdlib ``logging``
gets a ``server_id`` attribute set to the value returned by the provider, and
the value becomes available to formatters (including the platform
``JSONFormatter`` when configured with ``extra_fields=["server_id"]``).

Providers are stored in a module-level registry so multiple callers (a service
and the platform package itself) compose without overwriting each other; the
factory is installed exactly once per process.
"""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any, Callable

#: Type alias for a field provider callable. The callable takes no arguments
#: and returns the value to assign to the record attribute.
FieldProvider = Callable[[], Any]

_registry_lock = RLock()
_field_providers: dict[str, FieldProvider] = {}
_factory_installed: bool = False
_original_factory: Callable[..., logging.LogRecord] | None = None


def register_log_field_provider(name: str, provider: FieldProvider) -> None:
    """Register a callable that supplies a value for a per-record attribute.

    Each subsequent ``LogRecord`` created via stdlib ``logging`` (and therefore
    every record handled by ``cloud_dog_logging``) is given an attribute named
    ``name`` whose value is the result of ``provider()``. If the same ``name``
    is registered again, the previous provider is replaced (idempotent rebind).

    The first call to this function installs a chained ``logging`` record
    factory exactly once per process. Subsequent calls only mutate the
    registry, so call sites are safe to invoke multiple times.

    Args:
        name: Attribute name to set on the record. Must be a non-empty string
            and SHOULD NOT collide with stdlib ``LogRecord`` reserved fields
            (``msg``, ``levelname``, ``name``, ``args``, etc.) — collisions
            with reserved fields are rejected with ``ValueError`` to prevent
            silent corruption of the standard record schema.
        provider: A zero-argument callable returning the value. The callable
            is invoked once per record creation. Exceptions from the provider
            are swallowed and the attribute is set to ``None`` so a faulty
            provider can never break the logging path.

    Raises:
        ValueError: If ``name`` is empty or collides with a reserved
            ``LogRecord`` attribute.
        TypeError: If ``provider`` is not callable.

    Related tests: UT_LogRecordFactory
    """
    if not isinstance(name, str) or not name:
        raise ValueError("register_log_field_provider: name must be a non-empty string")
    if not callable(provider):
        raise TypeError("register_log_field_provider: provider must be callable")
    if name in _RESERVED_RECORD_ATTRS:
        raise ValueError(
            f"register_log_field_provider: '{name}' is a reserved LogRecord attribute and "
            "cannot be overridden by a field provider"
        )

    with _registry_lock:
        _field_providers[name] = provider
        _ensure_factory_installed_locked()


def unregister_log_field_provider(name: str) -> bool:
    """Remove a previously-registered field provider.

    Args:
        name: Attribute name previously passed to
            :func:`register_log_field_provider`.

    Returns:
        ``True`` if the provider was registered and has now been removed,
        ``False`` if no such provider was registered.

    Related tests: UT_LogRecordFactory
    """
    with _registry_lock:
        return _field_providers.pop(name, None) is not None


def clear_log_field_providers() -> None:
    """Remove every registered field provider.

    Primarily intended for test isolation. Does NOT uninstall the chained
    record factory (the factory becomes a no-op overlay over the original
    factory once the registry is empty), which keeps subsequent
    ``register_log_field_provider`` calls cheap and avoids races against
    other components that may hold a reference to the factory.

    Related tests: UT_LogRecordFactory
    """
    with _registry_lock:
        _field_providers.clear()


def get_registered_field_providers() -> dict[str, FieldProvider]:
    """Return a shallow copy of the current field-provider registry.

    Useful for diagnostic logging and for unit tests that want to assert
    on registry state without holding the internal lock.

    Related tests: UT_LogRecordFactory
    """
    with _registry_lock:
        return dict(_field_providers)


def _ensure_factory_installed_locked() -> None:
    """Install the chained record factory exactly once.

    Must be called while holding ``_registry_lock``.
    """
    global _factory_installed, _original_factory
    if _factory_installed:
        return

    _original_factory = logging.getLogRecordFactory()

    def _factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = _original_factory(*args, **kwargs)  # type: ignore[misc]
        # Snapshot the registry under the lock so a concurrent
        # register/unregister cannot mutate iteration ordering.
        with _registry_lock:
            providers = tuple(_field_providers.items())
        for attr_name, provider in providers:
            if hasattr(record, attr_name) and getattr(record, attr_name) not in (None, ""):
                # Caller-supplied extra fields take precedence over providers
                # so explicit log-call context is never overwritten.
                continue
            try:
                value = provider()
            except Exception:
                value = None
            try:
                setattr(record, attr_name, value)
            except Exception:
                # If the attribute name is somehow rejected by the record,
                # do not break the logging path.
                pass
        return record

    logging.setLogRecordFactory(_factory)
    _factory_installed = True


# Reserved stdlib LogRecord attributes that providers MUST NOT shadow.
# Sourced from Python 3.10+ ``logging.LogRecord`` attribute table.
_RESERVED_RECORD_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


__all__ = [
    "FieldProvider",
    "register_log_field_provider",
    "unregister_log_field_provider",
    "clear_log_field_providers",
    "get_registered_field_providers",
]
