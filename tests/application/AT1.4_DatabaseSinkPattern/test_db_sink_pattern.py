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

"""AT1.4: Database sink and fan-out pattern tests."""

from __future__ import annotations

import json
from pathlib import Path

from cloud_dog_logging.audit_logger import AuditLogger
from cloud_dog_logging.audit_schema import Actor
from cloud_dog_logging.batching import BatchingSink
from cloud_dog_logging.sinks import DatabaseSink, FanOutSink, FileSink


class _MockRepository:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def insert_event(self, event: dict) -> None:
        self.events.append(event)

    def insert_events(self, events: list[dict]) -> None:
        self.events.extend(events)


class _FailingSink:
    def emit(self, event) -> None:  # type: ignore[no-untyped-def]
        _ = event
        raise RuntimeError("db down")

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class TestDatabaseSinkPattern:
    def test_file_and_db_fanout_persists_to_both(self, tmp_path: Path) -> None:
        repo = _MockRepository()
        file_path = tmp_path / "audit.log.jsonl"

        sink = FanOutSink([DatabaseSink(repo), FileSink(str(file_path))])
        audit = AuditLogger(sink=sink, service_name="db-pattern")
        audit.log_login(actor=Actor(type="user", id="u-1"), outcome="success")
        audit.close()

        assert len(repo.events) == 1
        lines = file_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["event_type"] == "user.login"

    def test_batching_with_database_sink(self) -> None:
        repo = _MockRepository()
        batching = BatchingSink(DatabaseSink(repo), batch_size=2, flush_interval_s=5.0)
        audit = AuditLogger(sink=batching, service_name="db-batch")
        actor = Actor(type="user", id="u-1")

        audit.log_login(actor=actor, outcome="success")
        audit.log_login(actor=actor, outcome="success")
        audit.log_login(actor=actor, outcome="success")
        audit.close()

        assert len(repo.events) == 3

    def test_failing_db_sink_does_not_drop_fallback_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "audit.log.jsonl"
        sink = FanOutSink([_FailingSink(), FileSink(str(file_path))])  # type: ignore[list-item]
        audit = AuditLogger(sink=sink, service_name="db-fallback")
        audit.log_login(actor=Actor(type="user", id="u-1"), outcome="success")
        audit.close()

        lines = file_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
