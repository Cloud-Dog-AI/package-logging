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

"""System tests for periodic audit integrity verification."""

from __future__ import annotations

import json
import logging
import time
from io import StringIO
from pathlib import Path

from cloud_dog_logging.correlation import set_environment, set_service_instance, set_service_name
from cloud_dog_logging.formatters.json_formatter import JSONFormatter
from cloud_dog_logging.integrity import AuditIntegrityVerifier


def _append_event(path: Path, idx: int) -> None:
    payload = {
        "timestamp": f"2026-03-13T07:52:{idx:02d}.123Z",
        "event_type": "system_function",
        "action": "heartbeat",
        "outcome": "success",
    }
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload) + "\n")


def _read_integrity(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_startup_baseline(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _append_event(audit, 1)

    verifier = AuditIntegrityVerifier(str(audit), str(integrity), interval_seconds=1)
    verifier.start()
    time.sleep(0.2)
    verifier.stop()

    rows = _read_integrity(integrity)
    assert rows
    assert rows[0]["trigger"] == "startup"


def test_periodic_writes(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _append_event(audit, 1)

    verifier = AuditIntegrityVerifier(str(audit), str(integrity), interval_seconds=1)
    verifier.start()
    time.sleep(4.2)
    verifier.stop()

    rows = _read_integrity(integrity)
    assert len(rows) >= 3
    assert any(row["trigger"] == "periodic" for row in rows)


def test_shutdown_final_record(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _append_event(audit, 1)

    verifier = AuditIntegrityVerifier(str(audit), str(integrity), interval_seconds=2)
    verifier.start()
    time.sleep(0.2)
    verifier.stop()

    rows = _read_integrity(integrity)
    assert rows[-1]["trigger"] == "shutdown"


def test_rotation_trigger(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _append_event(audit, 1)

    verifier = AuditIntegrityVerifier(str(audit), str(integrity), interval_seconds=100)
    verifier.start()
    verifier.compute_now(trigger="rotation")
    verifier.stop()

    rows = _read_integrity(integrity)
    assert any(row["trigger"] == "rotation" for row in rows)


def test_integrity_log_file_exists(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _append_event(audit, 1)

    verifier = AuditIntegrityVerifier(str(audit), str(integrity), interval_seconds=1)
    verifier.start()
    time.sleep(0.2)
    verifier.stop()

    assert integrity.exists()
    assert integrity.read_text(encoding="utf-8").strip()


def test_periodic_app_log_uses_verifier_context(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _append_event(audit, 1)

    logger = logging.getLogger("cloud_dog_logging.integrity")
    original_handlers = list(logger.handlers)
    original_level = logger.level
    original_propagate = logger.propagate

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter())
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    set_service_name("wrong-service")
    set_service_instance("wrong-instance")
    set_environment("wrong-env")

    verifier = AuditIntegrityVerifier(
        str(audit),
        str(integrity),
        interval_seconds=1,
        service_name="file-mcp-server",
        service_instance="file-mcp-local",
        environment="dev",
    )
    try:
        verifier.start()
        time.sleep(1.2)
        verifier.stop()
    finally:
        handler.flush()
        logger.handlers = original_handlers
        logger.setLevel(original_level)
        logger.propagate = original_propagate

    rows = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
    periodic_rows = [
        row for row in rows if row.get("extra", {}).get("integrity_record", {}).get("trigger") == "periodic"
    ]
    assert periodic_rows
    assert periodic_rows[-1]["service"] == "file-mcp-server"
    assert periodic_rows[-1]["service_instance"] == "file-mcp-local"
    assert periodic_rows[-1]["environment"] == "dev"
