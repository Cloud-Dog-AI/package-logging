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

"""UT1.15: FanOut sink dispatch tests."""

from __future__ import annotations

from cloud_dog_logging.audit_schema import Actor, AuditEvent
from cloud_dog_logging.sinks.fan_out import FanOutSink


class _CaptureSink:
    def __init__(self) -> None:
        self.events = []
        self.flushed = 0
        self.closed = 0

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    def flush(self) -> None:
        self.flushed += 1

    def close(self) -> None:
        self.closed += 1


class _FailingSink:
    def emit(self, event: AuditEvent) -> None:
        _ = event
        raise RuntimeError("sink failed")

    def flush(self) -> None:
        raise RuntimeError("flush failed")

    def close(self) -> None:
        raise RuntimeError("close failed")


class TestFanOutSink:
    def test_one_sink_failure_does_not_block_others(self) -> None:
        ok = _CaptureSink()
        fan = FanOutSink([_FailingSink(), ok])
        fan.emit(
            AuditEvent(
                event_type="user.login",
                actor=Actor(type="user", id="u-1"),
                action="login",
                outcome="success",
                correlation_id="cid-1",
                service="test-service",
            )
        )
        assert len(ok.events) == 1

    def test_flush_and_close_propagated(self) -> None:
        ok = _CaptureSink()
        fan = FanOutSink([ok])
        fan.flush()
        fan.close()
        assert ok.flushed == 1
        assert ok.closed == 1
