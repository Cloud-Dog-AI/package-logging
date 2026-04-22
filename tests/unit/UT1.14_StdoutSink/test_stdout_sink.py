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

"""UT1.14: StdoutSink output tests."""

from __future__ import annotations

import json
from io import StringIO

from cloud_dog_logging.audit_schema import Actor, AuditEvent
from cloud_dog_logging.sinks.stdout_sink import StdoutSink


class TestStdoutSink:
    def test_writes_json_to_stdout_stream(self) -> None:
        stream = StringIO()
        sink = StdoutSink(stream=stream)
        sink.emit(
            AuditEvent(
                event_type="user.login",
                actor=Actor(type="user", id="u-1"),
                action="login",
                outcome="success",
                correlation_id="cid-1",
                service="test-service",
            )
        )
        sink.flush()
        output = stream.getvalue().strip()
        parsed = json.loads(output)
        assert parsed["event_type"] == "user.login"
        assert parsed["actor"]["id"] == "u-1"

    def test_flush_and_close_are_safe(self) -> None:
        stream = StringIO()
        sink = StdoutSink(stream=stream)
        sink.flush()
        sink.close()
