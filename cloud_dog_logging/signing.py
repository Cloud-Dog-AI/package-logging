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

# cloud_dog_logging — Audit signing hooks
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Optional signing hooks for tamper-evident audit records.
# Related requirements: FR1.19
# Related architecture: CC1.12

"""Audit signing hooks for tamper-evident persistence."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import replace
from typing import Protocol

from cloud_dog_logging.audit_schema import AuditEvent


class AuditSigner(Protocol):
    """Protocol for audit signing hooks."""

    def pre_persist(self, event: AuditEvent) -> AuditEvent:
        """Transform an event before sink persistence."""

    def post_persist(self, event: AuditEvent) -> None:
        """Run after sink persistence."""


class HMACSigner:
    """HMAC-SHA256 signer with simple hash chaining."""

    def __init__(self, secret_key: str) -> None:
        if not secret_key:
            raise ValueError("HMACSigner requires a non-empty secret key")
        self._key = secret_key.encode("utf-8")
        self._last_signature: str | None = None

    def pre_persist(self, event: AuditEvent) -> AuditEvent:
        """Handle pre persist."""
        details = dict(event.details or {})
        if self._last_signature is not None:
            details["_prev_signature"] = self._last_signature

        canonical_event = event.to_dict()
        canonical_event["details"] = details
        payload = json.dumps(canonical_event, sort_keys=True, separators=(",", ":"), default=str)
        signature = hmac.new(self._key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        details["_signature"] = signature
        return replace(event, details=details)

    def post_persist(self, event: AuditEvent) -> None:
        """Handle post persist."""
        details = event.details or {}
        signature = details.get("_signature")
        if isinstance(signature, str) and signature:
            self._last_signature = signature

    @property
    def last_signature(self) -> str | None:
        """Return the current end-of-chain signature."""
        return self._last_signature
