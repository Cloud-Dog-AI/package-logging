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

# cloud_dog_logging — Structured JSON Lines formatter
#
# Licence: Apache 2.0 — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Formats log records as JSON Lines (one JSON object per line).
#   Includes all required fields from FR1.3/FR1.4. Handles exceptions by
#   serialising tracebacks as strings. Provides ``add_json_field`` registry
#   for additive top-level JSON fields without monkey-patching.
# Related requirements: FR1.2, FR1.4
# Related architecture: CC1.6

"""Structured JSON Lines formatter for both log streams.

Public ``add_json_field`` registry
-----------------------------------

Services that need to emit additional top-level JSON fields (for example
``severity``, ``event_type``, ``request_id``, or any service-specific marker)
register a provider callable via :func:`add_json_field`. Each registered
provider is invoked once per record by every :class:`JSONFormatter` instance
in the process and the returned value is added to the JSON output AFTER the
stable schema fields. Stable schema fields are never overwritten.

Compared to the legacy approach (subclass :class:`JSONFormatter` or
monkey-patch its ``format`` method) this:

1. Composes — multiple services or middleware layers can each register their
   own field without conflicting.
2. Is testable in isolation via :func:`clear_json_fields`.
3. Closes RULES.md §1.4 violations where services kept bespoke
   ``logger.py`` wrappers solely to inject custom JSON fields.
"""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable

from cloud_dog_logging.correlation import (
    get_correlation_id,
    get_environment,
    get_service_instance,
    get_service_name,
)


#: Type alias for a JSON-field provider callable. The callable accepts a
#: :class:`logging.LogRecord` and returns the value to emit (or ``None`` to
#: skip emission for that record).
JSONFieldProvider = Callable[[logging.LogRecord], Any]


_json_field_lock = RLock()
_json_field_providers: "dict[str, JSONFieldProvider]" = {}


# Stable schema field names that providers MUST NOT overwrite. Stays in sync
# with the literal keys assigned in :meth:`JSONFormatter.format` below.
_STABLE_SCHEMA_FIELDS = frozenset(
    {
        "timestamp",
        "level",
        "logger",
        "message",
        "correlation_id",
        "service",
        "service_instance",
        "environment",
        "extra",
        "traceback",
        "stack_info",
    }
)


def add_json_field(name: str, provider: JSONFieldProvider) -> None:
    """Register a process-wide JSON-output field provider.

    Each subsequent JSON-formatted log line will include a top-level field
    whose key is ``name`` and whose value is the result of ``provider(record)``.
    Re-registering the same ``name`` replaces the previous provider
    (idempotent rebind).

    Args:
        name: The JSON object key. Must be a non-empty string and MUST NOT
            collide with stable schema fields (``timestamp``, ``level``,
            ``logger``, ``message``, ``correlation_id``, ``service``,
            ``service_instance``, ``environment``, ``extra``, ``traceback``,
            ``stack_info``).
        provider: A callable taking a :class:`logging.LogRecord` and returning
            the value. Provider exceptions are swallowed (the field is then
            simply omitted from the line) so a faulty provider can never
            break the logging path.

    Raises:
        ValueError: If ``name`` is empty or collides with a stable schema
            field.
        TypeError: If ``provider`` is not callable.

    Related tests: UT_JSONFieldRegistry
    """
    if not isinstance(name, str) or not name:
        raise ValueError("add_json_field: name must be a non-empty string")
    if name in _STABLE_SCHEMA_FIELDS:
        raise ValueError(
            f"add_json_field: '{name}' is a stable schema field and cannot be "
            "overridden by a provider"
        )
    if not callable(provider):
        raise TypeError("add_json_field: provider must be callable")
    with _json_field_lock:
        _json_field_providers[name] = provider


def remove_json_field(name: str) -> bool:
    """Remove a previously-registered JSON-field provider.

    Returns:
        ``True`` if a provider with that name was removed, ``False`` otherwise.

    Related tests: UT_JSONFieldRegistry
    """
    with _json_field_lock:
        return _json_field_providers.pop(name, None) is not None


def clear_json_fields() -> None:
    """Remove every registered JSON-field provider.

    Primarily intended for test isolation.

    Related tests: UT_JSONFieldRegistry
    """
    with _json_field_lock:
        _json_field_providers.clear()


def get_registered_json_fields() -> "dict[str, JSONFieldProvider]":
    """Return a shallow copy of the current JSON-field provider registry.

    Related tests: UT_JSONFieldRegistry
    """
    with _json_field_lock:
        return dict(_json_field_providers)


class JSONFormatter(logging.Formatter):
    """Structured JSON Lines formatter for cloud_dog_logging.

    Produces one JSON object per line with all required fields:
    timestamp, level, logger, message, correlation_id, service, extra.

    Exceptions are serialised as a ``traceback`` string field within the
    JSON object.

    Args:
        service_name: Override service name (otherwise read from context).
        include_extra: Whether to include extra fields. Defaults to True.
        extra_fields: Optional list of record-attribute names to emit as
            top-level JSON fields (in addition to the default schema). This
            is the documented integration point for record attributes
            populated via ``register_log_field_provider`` (e.g.
            ``["server_id"]``). Each named attribute, if present on the
            record and not already a stdlib reserved attribute, becomes a
            top-level field on the output object. Defaults to ``None``
            (no top-level promotion), which preserves prior behaviour for
            existing callers.

    Top-level fields registered via :func:`add_json_field` are emitted AFTER
    the stable schema and ``extra_fields`` promotions. Provider failures and
    duplicates with stable-schema names are silently dropped so providers
    cannot corrupt the canonical schema.

    Related tests: UT1.1_JSONFormatter, UT_JSONFormatterCustomFields,
        UT_JSONFieldRegistry
    """

    def __init__(
        self,
        service_name: str | None = None,
        include_extra: bool = True,
        extra_fields: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._service_name = service_name
        self._include_extra = include_extra
        self._extra_fields: tuple[str, ...] = tuple(extra_fields or ())
        self._reserved_attrs = frozenset(
            {
                "name",
                "msg",
                "args",
                "created",
                "relativeCreated",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "pathname",
                "filename",
                "module",
                "thread",
                "threadName",
                "process",
                "processName",
                "levelname",
                "levelno",
                "msecs",
                "message",
                "taskName",
            }
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A JSON string representing the log entry (no trailing newline).

        Related tests: UT1.1_JSONFormatter
        """
        # Ensure message is resolved
        record.message = record.getMessage()

        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        service = self._service_name or get_service_name()

        entry: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "correlation_id": get_correlation_id(),
            "service": service,
            "service_instance": get_service_instance(),
            "environment": get_environment(),
        }

        # Promote registered field-provider attributes (e.g. server_id) to
        # the top level of the JSON output so structured-log consumers do not
        # need to dig into the ``extra`` sub-object for fields that the
        # service has declared as first-class.
        for field_name in self._extra_fields:
            if field_name in self._reserved_attrs:
                # Never overwrite stdlib reserved fields via this path.
                continue
            if not hasattr(record, field_name):
                continue
            value = getattr(record, field_name)
            try:
                json.dumps(value)
                entry[field_name] = value
            except (TypeError, ValueError):
                entry[field_name] = str(value)

        # Include extra fields from the record
        if self._include_extra:
            extra: dict[str, Any] = {}
            promoted = set(self._extra_fields)
            for key, value in record.__dict__.items():
                if key in self._reserved_attrs or key.startswith("_"):
                    continue
                if key in promoted:
                    # Already emitted as a top-level field — do not duplicate
                    # under ``extra`` to keep output deterministic.
                    continue
                try:
                    json.dumps(value)
                    extra[key] = value
                except (TypeError, ValueError):
                    extra[key] = str(value)
            if extra:
                entry["extra"] = extra

        # Handle exceptions
        if record.exc_info and record.exc_info[0] is not None:
            entry["traceback"] = "".join(traceback.format_exception(*record.exc_info))

        if record.stack_info:
            entry["stack_info"] = record.stack_info

        # Append values from the global JSON-field registry. Stable schema
        # fields are protected (re-asserted here as a defence in depth in
        # case ``add_json_field`` was bypassed). Provider exceptions are
        # swallowed so a faulty provider cannot break the logging path.
        with _json_field_lock:
            providers = tuple(_json_field_providers.items())
        for field_name, provider in providers:
            if field_name in _STABLE_SCHEMA_FIELDS:
                continue
            try:
                value = provider(record)
            except Exception:
                continue
            if value is None:
                continue
            try:
                json.dumps(value)
                entry[field_name] = value
            except (TypeError, ValueError):
                entry[field_name] = str(value)

        return json.dumps(entry, default=str, ensure_ascii=False)
