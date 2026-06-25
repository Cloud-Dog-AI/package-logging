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

"""UT1.12: Audit sink protocol and integration tests."""

from __future__ import annotations

from cloud_dog_logging.audit_logger import AuditLogger
from cloud_dog_logging.audit_schema import Actor


class _MemorySink:
    def __init__(self) -> None:
        self.events = []
        self.flushed = False
        self.closed = False

    def emit(self, event) -> None:  # type: ignore[no-untyped-def]
        self.events.append(event)

    def flush(self) -> None:
        self.flushed = True

    def close(self) -> None:
        self.closed = True


class TestAuditSinkInterface:
    def test_custom_sink_works_with_audit_logger(self) -> None:
        sink = _MemorySink()
        audit = AuditLogger(sink=sink, service_name="test-service")
        audit.log_login(actor=Actor(type="user", id="u-1"), outcome="success")

        assert len(sink.events) == 1
        assert sink.events[0].event_type == "user.login"
        audit.flush()
        audit.close()
        assert sink.flushed is True
        assert sink.closed is True

    def test_invalid_sink_rejected(self) -> None:
        class _InvalidSink:
            def emit(self, event) -> None:  # type: ignore[no-untyped-def]
                _ = event

        try:
            AuditLogger(sink=_InvalidSink(), service_name="test-service")  # type: ignore[arg-type]
            assert False, "Expected TypeError for invalid sink"
        except TypeError as exc:
            assert "missing callable 'flush'" in str(exc)
