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

"""UT1.20: BatchingSink flush semantics tests."""

from __future__ import annotations

import time

from cloud_dog_logging.audit_schema import Actor, AuditEvent
from cloud_dog_logging.batching import BatchingSink


def _event(idx: int) -> AuditEvent:
    return AuditEvent(
        event_type="user.login",
        actor=Actor(type="user", id=f"u-{idx}"),
        action="login",
        outcome="success",
        correlation_id=f"cid-{idx}",
        service="batch-test",
        details={"idx": idx},
    )


class _CaptureSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []
        self.flush_calls = 0

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    def flush(self) -> None:
        self.flush_calls += 1

    def close(self) -> None:
        pass


class _BatchCaptureSink(_CaptureSink):
    def emit_batch(self, events: list[AuditEvent]) -> None:
        self.events.extend(events)


class TestAuditBatching:
    def test_flush_on_batch_size(self) -> None:
        sink = _CaptureSink()
        batching = BatchingSink(sink=sink, batch_size=3, flush_interval_s=5.0)
        batching.emit(_event(1))
        batching.emit(_event(2))
        assert len(sink.events) == 0
        batching.emit(_event(3))
        assert [e.details["idx"] for e in sink.events] == [1, 2, 3]  # type: ignore[index]

    def test_flush_on_interval(self) -> None:
        sink = _CaptureSink()
        batching = BatchingSink(sink=sink, batch_size=100, flush_interval_s=0.01)
        batching.emit(_event(1))
        time.sleep(0.02)
        batching.emit(_event(2))
        assert len(sink.events) == 2

    def test_close_flushes_remaining(self) -> None:
        sink = _CaptureSink()
        batching = BatchingSink(sink=sink, batch_size=10, flush_interval_s=5.0)
        batching.emit(_event(1))
        batching.close()
        assert len(sink.events) == 1

    def test_emit_batch_used_when_available(self) -> None:
        sink = _BatchCaptureSink()
        batching = BatchingSink(sink=sink, batch_size=2, flush_interval_s=5.0)
        batching.emit(_event(1))
        batching.emit(_event(2))
        assert [e.details["idx"] for e in sink.events] == [1, 2]  # type: ignore[index]
