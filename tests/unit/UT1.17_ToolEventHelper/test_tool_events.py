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

"""UT1.17: log_tool_event helper tests."""

from __future__ import annotations

from cloud_dog_logging import log_tool_event
from cloud_dog_logging.audit_logger import AuditLogger
from cloud_dog_logging.correlation import set_correlation_id, set_service_name


class _CaptureSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:  # type: ignore[no-untyped-def]
        self.events.append(event)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class TestToolEventHelper:
    def test_log_tool_event_emits_standard_event(self) -> None:
        import cloud_dog_logging

        sink = _CaptureSink()
        cloud_dog_logging._audit_logger = AuditLogger(sink=sink, service_name="tool-service")
        set_service_name("tool-service")
        set_correlation_id("tool-cid-1")

        log_tool_event(
            tool="read_file",
            profile="default",
            duration_ms=15,
            paths=["/tmp/a.txt"],
            outcome="success",
            token="abc123",
        )

        assert len(sink.events) == 1
        event = sink.events[0]
        payload = event.to_dict()
        assert payload["event_type"] == "tool_call"
        assert payload["details"]["tool"] == "read_file"
        assert payload["details"]["profile"] == "default"
        assert payload["details"]["paths"] == ["/tmp/a.txt"]
        assert payload["correlation_id"] == "tool-cid-1"
