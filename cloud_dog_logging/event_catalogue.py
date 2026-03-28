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

# cloud_dog_logging — Event catalogue validator
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Helper for validating emitted audit events against a declared
#   service event catalogue.
# Related requirements: FR1.10
# Related architecture: CC1.18

"""Event catalogue helper for optional runtime event validation."""

from __future__ import annotations

import json
from pathlib import Path

from cloud_dog_logging.audit_schema import AuditEvent


class EventCatalogue:
    """Validate audit events against a declared event catalogue."""

    def __init__(self, catalogue_path: str) -> None:
        self._path = Path(catalogue_path)
        self._allowed = self._load_catalogue(self._path)

    @staticmethod
    def _load_catalogue(path: Path) -> set[str]:
        if not path.exists():
            return set()

        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return {str(item) for item in payload}
            if isinstance(payload, dict):
                events = payload.get("event_types", [])
                if isinstance(events, list):
                    return {str(item) for item in events}
            return set()

        allowed: set[str] = set()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("|"):
                parts = [part.strip() for part in stripped.strip("|").split("|")]
                if parts and parts[0] and parts[0].lower() != "event_type":
                    allowed.add(parts[0].strip("`"))
                continue
            if stripped.startswith("-"):
                token = stripped.lstrip("- ").split(" ", 1)[0].strip("`")
                if token:
                    allowed.add(token)
        return allowed

    def validate(self, event: AuditEvent) -> bool:
        """Validate an audit event against the loaded catalogue."""
        if not self._allowed:
            return True
        return event.event_type in self._allowed
