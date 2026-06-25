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

"""Unit tests for audit integrity verifier hash and record generation."""

from __future__ import annotations

import binascii
import hashlib
import json
import logging
from pathlib import Path

from cloud_dog_logging.integrity import AuditIntegrityVerifier


AUDIT_LINE = {
    "timestamp": "2026-03-13T07:52:45.123Z",
    "event_type": "user.login",
    "action": "login",
    "outcome": "success",
}


def _write_audit(path: Path, count: int = 1) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for _ in range(count):
            stream.write(json.dumps(AUDIT_LINE) + "\n")


def test_hash_computation_sha256(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _write_audit(audit, count=2)

    verifier = AuditIntegrityVerifier(
        audit_log_path=str(audit),
        integrity_log_path=str(integrity),
        hash_algorithm="sha256",
        service_name="svc",
        service_instance="svc-1",
    )
    record = verifier.compute_now()

    expected = hashlib.sha256(audit.read_bytes()).hexdigest()
    assert record["hash_value"] == expected
    assert record["verification_status"] == "valid"


def test_hash_computation_sha512(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _write_audit(audit)

    verifier = AuditIntegrityVerifier(str(audit), str(integrity), hash_algorithm="sha512")
    record = verifier.compute_now()

    expected = hashlib.sha512(audit.read_bytes()).hexdigest()
    assert record["hash_value"] == expected


def test_hash_computation_crc32(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _write_audit(audit)

    verifier = AuditIntegrityVerifier(str(audit), str(integrity), hash_algorithm="crc32")
    record = verifier.compute_now()

    expected = format(binascii.crc32(audit.read_bytes()) & 0xFFFFFFFF, "08x")
    assert record["hash_value"] == expected


def test_record_format(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _write_audit(audit)

    verifier = AuditIntegrityVerifier(str(audit), str(integrity), service_name="chat-client", service_instance="c0")
    record = verifier.compute_now(trigger="manual")

    required = {
        "timestamp",
        "record_type",
        "service",
        "service_instance",
        "audit_log_path",
        "hash_algorithm",
        "hash_value",
        "file_size_bytes",
        "line_count",
        "last_event_timestamp",
        "verification_status",
        "trigger",
    }
    assert required.issubset(set(record.keys()))
    assert record["record_type"] == "audit_integrity_check"


def test_missing_audit_file(tmp_path: Path) -> None:
    audit = tmp_path / "missing.log"
    integrity = tmp_path / "audit-integrity.log"

    verifier = AuditIntegrityVerifier(str(audit), str(integrity))
    record = verifier.compute_now()

    assert record["verification_status"] == "error"
    assert record["hash_value"] == ""


def test_empty_audit_file(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    audit.write_text("", encoding="utf-8")

    verifier = AuditIntegrityVerifier(str(audit), str(integrity), hash_algorithm="sha256")
    record = verifier.compute_now()

    expected = hashlib.sha256(b"").hexdigest()
    assert record["hash_value"] == expected
    assert record["file_size_bytes"] == 0


def test_compute_now_skips_closed_logger_stream(tmp_path: Path) -> None:
    audit = tmp_path / "audit.log.jsonl"
    integrity = tmp_path / "audit-integrity.log"
    _write_audit(audit)

    logger = logging.getLogger("cloud_dog_logging.integrity")
    logger.handlers.clear()
    logger.propagate = False

    closed_stream = (tmp_path / "closed.log").open("w", encoding="utf-8")
    handler = logging.StreamHandler(closed_stream)
    logger.addHandler(handler)
    closed_stream.close()

    verifier = AuditIntegrityVerifier(str(audit), str(integrity))
    record = verifier.compute_now(trigger="shutdown")

    logger.removeHandler(handler)
    handler.close()
    logger.propagate = True

    rows = [json.loads(line) for line in integrity.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert record["trigger"] == "shutdown"
    assert rows[-1]["trigger"] == "shutdown"
