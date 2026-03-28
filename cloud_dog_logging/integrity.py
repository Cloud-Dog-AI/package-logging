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

# cloud_dog_logging — Audit log integrity verification
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Periodic hash verification for audit log files with JSONL
#   integrity records for AU-9/AU-16 style controls.
# Related requirements: FR1.25, FR1.26
# Related architecture: CC1.18

"""Audit integrity verifier for periodic hash checks of audit log files."""

from __future__ import annotations

import binascii
import hashlib
import json
import logging
import sys
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditIntegrityVerifier:
    """Periodic SHA-256 hash verification of audit log files (L14, AU-9)."""

    def __init__(
        self,
        audit_log_path: str,
        integrity_log_path: str = "logs/audit-integrity.log",
        interval_seconds: int = 300,
        hash_algorithm: str = "sha256",
        service_name: str | None = None,
        service_instance: str | None = None,
    ) -> None:
        self._audit_log_path = Path(audit_log_path)
        self._integrity_log_path = Path(integrity_log_path)
        self._interval_seconds = max(1, int(interval_seconds))
        self._hash_algorithm = (hash_algorithm or "sha256").lower()
        if self._hash_algorithm not in {"sha256", "sha512", "crc32"}:
            self._hash_algorithm = "sha256"
        self._service_name = service_name or "unknown"
        self._service_instance = service_instance or socket.gethostname()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._logger = logging.getLogger("cloud_dog_logging.integrity")

    def start(self) -> None:
        """Start background verification thread. Writes baseline immediately."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self.compute_now(trigger="startup")
            self._thread = threading.Thread(
                target=self._run_loop,
                name="cloud-dog-audit-integrity",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Stop background thread. Writes final integrity record."""
        with self._lock:
            self._stop_event.set()
            thread = self._thread
            self._thread = None

        if thread is not None:
            thread.join(timeout=max(2, self._interval_seconds + 1))

        self.compute_now(trigger="shutdown")

    def compute_now(self, trigger: str = "manual") -> dict[str, Any]:
        """Compute integrity hash immediately and return integrity record."""
        hash_data = self._compute_hash()
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "record_type": "audit_integrity_check",
            "service": self._service_name,
            "service_instance": self._service_instance,
            "audit_log_path": str(self._audit_log_path),
            "hash_algorithm": self._hash_algorithm,
            "hash_value": hash_data["hash_value"],
            "file_size_bytes": hash_data["file_size_bytes"],
            "line_count": hash_data["line_count"],
            "last_event_timestamp": hash_data["last_event_timestamp"],
            "verification_status": hash_data["verification_status"],
            "trigger": trigger,
        }
        self._write_integrity_record(record)
        return record

    def _compute_hash(self) -> dict[str, Any]:
        """Compute hash of audit log file and return metadata."""
        if not self._audit_log_path.exists():
            return {
                "hash_value": "",
                "file_size_bytes": 0,
                "line_count": 0,
                "last_event_timestamp": None,
                "verification_status": "error",
            }

        try:
            file_size = self._audit_log_path.stat().st_size

            if self._hash_algorithm == "crc32":
                crc = 0
                with self._audit_log_path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        crc = binascii.crc32(chunk, crc)
                hash_value = format(crc & 0xFFFFFFFF, "08x")
            else:
                hasher = hashlib.sha512() if self._hash_algorithm == "sha512" else hashlib.sha256()
                with self._audit_log_path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        hasher.update(chunk)
                hash_value = hasher.hexdigest()

            line_count = 0
            last_event_timestamp: str | None = None
            with self._audit_log_path.open("r", encoding="utf-8", errors="replace") as stream:
                for raw in stream:
                    line = raw.strip()
                    if not line:
                        continue
                    line_count += 1
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    ts = payload.get("timestamp")
                    if isinstance(ts, str) and ts:
                        last_event_timestamp = ts

            return {
                "hash_value": hash_value,
                "file_size_bytes": file_size,
                "line_count": line_count,
                "last_event_timestamp": last_event_timestamp,
                "verification_status": "valid",
            }
        except Exception:
            return {
                "hash_value": "",
                "file_size_bytes": 0,
                "line_count": 0,
                "last_event_timestamp": None,
                "verification_status": "error",
            }

    def _write_integrity_record(self, record: dict[str, Any]) -> None:
        """Write JSON record to app log and dedicated integrity log file."""
        if self._can_emit_to_logger():
            try:
                self._logger.info("audit_integrity_check", extra={"integrity_record": record})
            except (OSError, ValueError):
                # Late shutdown can close stream handlers before the verifier stops.
                pass
        self._integrity_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._integrity_log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _run_loop(self) -> None:
        """Background daemon loop for periodic hash checks."""
        while not self._stop_event.wait(self._interval_seconds):
            self.compute_now(trigger="periodic")

    def _can_emit_to_logger(self) -> bool:
        """Return True when all effective logger streams still look writable."""
        logger: logging.Logger | None = self._logger
        found_handler = False
        while logger is not None:
            for handler in logger.handlers:
                found_handler = True
                stream = getattr(handler, "stream", None)
                if stream is None:
                    continue
                if getattr(stream, "closed", False):
                    return False
                if stream in {sys.stdout, sys.stderr} and getattr(stream, "closed", False):
                    return False
            if not logger.propagate:
                break
            logger = logger.parent
        return found_handler
