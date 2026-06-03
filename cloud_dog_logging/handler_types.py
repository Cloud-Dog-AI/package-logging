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

# cloud_dog_logging — Declarative handler enum
#
# Licence: Apache 2.0 — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: ``HandlerType`` enum for declarative handler configuration in
#   ``setup_logging``. Lets callers say ``handlers=["dual"]`` (or
#   ``[HandlerType.DUAL]``) instead of constructing handler instances by hand.
# Related requirements: FR1.11
# Related architecture: CC1.9
# Related tests: UT_HandlerEnum

"""Declarative handler-type enum for ``cloud_dog_logging.setup_logging``.

The enum lets services express handler intent without importing handler
classes or repeating the file-vs-stream wiring already encapsulated in
``setup_logging``. The enum is additive — pre-existing dict-based handler
selection (``console: True``, ``app_log_file: ...``) continues to behave
exactly as before. When ``handlers=[...]`` is also supplied, the enum
selection is intersected with the existing dict knobs (an explicit
``CONSOLE`` selection forces ``console_output = True``, etc.).
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable


class HandlerType(str, Enum):
    """Declarative handler types accepted by ``setup_logging(handlers=[...])``.

    Members:
        FILE: A single file handler writing to ``log.app_log`` with rotation
            disabled (rotation defaults still apply via ``ConfigurableRotatingHandler``
            which supports rotation = "size"|"time"|"both"|"none").
        CONSOLE: A stdout-only handler. Equivalent to setting
            ``console_output=True`` and leaving ``app_log_file`` unset.
        DUAL: File + stdout via ``DualHandler``. Equivalent to the legacy
            "both ``app_log_file`` AND ``console=True``" combination but
            expressed declaratively.
        ROTATING: Same as ``FILE`` but emphasises rotation is active. Provided
            because services use it as a documentation hint; functionally
            identical to ``FILE`` because the platform rotating-file handler
            is the only file handler implementation.
    """

    FILE = "file"
    CONSOLE = "console"
    DUAL = "dual"
    ROTATING = "rotating"

    @classmethod
    def coerce(cls, value: object) -> "HandlerType":
        """Coerce a string or ``HandlerType`` into a ``HandlerType``.

        Accepts case-insensitive strings (e.g. ``"Dual"``) for ergonomic
        config-file integration.

        Raises:
            ValueError: If ``value`` is not a recognised handler type.
        """
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            try:
                return cls(value.lower().strip())
            except ValueError as exc:  # re-raise with a clearer message
                allowed = ", ".join(member.value for member in cls)
                raise ValueError(
                    f"HandlerType: '{value}' is not a recognised handler type "
                    f"(allowed: {allowed})"
                ) from exc
        raise ValueError(
            f"HandlerType: cannot coerce {type(value).__name__} into HandlerType"
        )

    @classmethod
    def coerce_many(cls, values: Iterable[object] | None) -> list["HandlerType"]:
        """Coerce an iterable of values into a list of ``HandlerType`` members.

        ``None`` is treated as an empty list so callers can pass through a
        missing config key without special-casing.
        """
        if values is None:
            return []
        return [cls.coerce(v) for v in values]


__all__ = ["HandlerType"]
