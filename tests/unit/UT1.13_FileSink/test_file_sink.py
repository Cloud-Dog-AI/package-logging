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

"""UT1.13: FileSink JSONL output tests."""

from __future__ import annotations

import json
from pathlib import Path

from cloud_dog_logging.audit_schema import Actor, AuditEvent
from cloud_dog_logging.sinks.file_sink import FileSink


def _event(idx: int) -> AuditEvent:
    return AuditEvent(
        event_type="user.login",
        actor=Actor(type="user", id=f"u-{idx}"),
        action="login",
        outcome="success",
        correlation_id=f"cid-{idx}",
        service="test-service",
        details={"index": idx},
    )


class TestFileSink:
    def test_writes_jsonl(self, tmp_path: Path) -> None:
        path = tmp_path / "audit.log.jsonl"
        sink = FileSink(str(path))
        sink.emit(_event(1))
        sink.close()

        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_type"] == "user.login"
        assert parsed["details"]["index"] == 1
        assert (path.stat().st_mode & 0o777) == 0o600

    def test_append_only_behavior(self, tmp_path: Path) -> None:
        path = tmp_path / "audit.log.jsonl"
        sink_a = FileSink(str(path))
        sink_a.emit(_event(1))
        sink_a.close()

        sink_b = FileSink(str(path))
        sink_b.emit(_event(2))
        sink_b.close()

        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["details"]["index"] == 1
        assert json.loads(lines[1])["details"]["index"] == 2
