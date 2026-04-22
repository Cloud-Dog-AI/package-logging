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

# cloud_dog_logging — Log health reporter
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Observability data for the log subsystem — file sizes,
#   rotation status, audit event count, last audit timestamp.
# Related requirements: FR1.12
# Related architecture: CC1.10

"""Log health reporter for cloud_dog_logging."""

from __future__ import annotations

import os
from typing import Any


class LogHealthReporter:
    """Observability data for the log subsystem.

    Reports file sizes, rotation status, audit event count, and last
    audit event timestamp for health/status endpoints.

    Args:
        app_log_path: Path to the application log file.
        audit_log_path: Path to the audit log file.
        audit_logger: Reference to the AuditLogger for event count/timestamp.

    Related tests: UT1.9_HealthReporter
    """

    def __init__(
        self,
        app_log_path: str | None = None,
        audit_log_path: str | None = None,
        audit_logger: Any = None,
    ) -> None:
        self._app_log_path = app_log_path
        self._audit_log_path = audit_log_path
        self._audit_logger = audit_logger

    def _get_file_size(self, path: str | None) -> int | None:
        """Get file size in bytes, or None if file does not exist.

        Args:
            path: The file path to check.

        Returns:
            File size in bytes, or None.
        """
        if path is None:
            return None
        try:
            return os.path.getsize(path)
        except OSError:
            return None

    def _count_rotated_files(self, path: str | None) -> int:
        """Count rotated backup files for a log path.

        Args:
            path: The base log file path.

        Returns:
            Number of rotated backup files found.
        """
        if path is None:
            return 0
        count = 0
        idx = 1
        while True:
            rotated = f"{path}.{idx}"
            if os.path.exists(rotated):
                count += 1
                idx += 1
            else:
                break
        return count

    def get_status(self) -> dict[str, Any]:
        """Return health/observability data for the logging subsystem.

        Returns:
            A dictionary containing:
            - ``app_log_size_bytes``: Size of the application log file.
            - ``audit_log_size_bytes``: Size of the audit log file.
            - ``app_log_rotated_files``: Number of rotated app log backups.
            - ``audit_log_rotated_files``: Number of rotated audit log backups.
            - ``audit_event_count``: Total audit events emitted since startup.
            - ``last_audit_event_timestamp``: Timestamp of the last audit event.

        Related tests: UT1.9_HealthReporter
        """
        result: dict[str, Any] = {
            "app_log_size_bytes": self._get_file_size(self._app_log_path),
            "audit_log_size_bytes": self._get_file_size(self._audit_log_path),
            "app_log_rotated_files": self._count_rotated_files(self._app_log_path),
            "audit_log_rotated_files": self._count_rotated_files(self._audit_log_path),
            "audit_event_count": 0,
            "last_audit_event_timestamp": None,
            "audit_sink_healthy": True,
        }
        if self._audit_logger is not None:
            result["audit_event_count"] = getattr(self._audit_logger, "event_count", 0)
            result["last_audit_event_timestamp"] = getattr(self._audit_logger, "last_event_timestamp", None)
            result["audit_sink_healthy"] = getattr(self._audit_logger, "audit_sink_healthy", True)
        return result
