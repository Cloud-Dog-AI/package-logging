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

"""UT1.6: Audit Logger — typed audit event emission tests."""

from __future__ import annotations

import json
import logging
from io import StringIO
from pathlib import Path

from cloud_dog_logging.audit_logger import AuditLogger
from cloud_dog_logging.audit_schema import Actor, Target
from cloud_dog_logging.correlation import set_correlation_id, set_service_name
from cloud_dog_logging.redaction import RedactionEngine


class TestAuditLogger:
    """Test suite for AuditLogger."""

    def setup_method(self) -> None:
        set_correlation_id("audit-corr-001")
        set_service_name("test-service")
        self.stream = StringIO()
        handler = logging.StreamHandler(self.stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.py_logger = logging.getLogger("test.audit_logger")
        self.py_logger.handlers.clear()
        self.py_logger.addHandler(handler)
        self.py_logger.setLevel(logging.DEBUG)
        self.py_logger.propagate = False
        self.audit = AuditLogger(
            logger=self.py_logger,
            redaction_engine=RedactionEngine(),
            service_name="test-service",
        )
        self.actor = Actor(type="user", id="u-1")

    def _get_last_event(self) -> dict:
        output = self.stream.getvalue().strip()
        lines = output.split("\n")
        return json.loads(lines[-1])

    def test_log_login_generates_event(self) -> None:
        self.audit.log_login(actor=self.actor, outcome="success", ip="127.0.0.1")
        event = self._get_last_event()
        assert event["event_type"] == "user.login"
        assert event["action"] == "login"
        assert event["outcome"] == "success"
        assert event["actor"]["id"] == "u-1"
        assert event["details"]["ip"] == "127.0.0.1"

    def test_log_crud_generates_event(self) -> None:
        target = Target(type="user", id="u-2")
        self.audit.log_crud(actor=self.actor, action="create", target=target, outcome="success")
        event = self._get_last_event()
        assert event["event_type"] == "user.create"
        assert event["action"] == "create"
        assert event["target"]["type"] == "user"
        assert event["target"]["id"] == "u-2"

    def test_log_config_change_generates_event(self) -> None:
        diff = {"changed": ["log.level"], "old": "INFO", "new": "DEBUG"}
        self.audit.log_config_change(actor=self.actor, diff_summary=diff, outcome="success")
        event = self._get_last_event()
        assert event["event_type"] == "config.change"
        assert event["action"] == "update"

    def test_log_tool_call_generates_event(self) -> None:
        self.audit.log_tool_call(
            actor=self.actor,
            tool="search",
            params={"query": "test"},
            outcome="success",
            duration_ms=150,
        )
        event = self._get_last_event()
        assert event["event_type"] == "tool.call"
        assert event["action"] == "execute"
        assert event["duration_ms"] == 150

    def test_log_security_generates_event(self) -> None:
        target = Target(type="user", id="u-3")
        self.audit.log_security(actor=self.actor, action="lockout", target=target, outcome="success")
        event = self._get_last_event()
        assert event["event_type"] == "security.lockout"
        assert event["action"] == "lockout"

    def test_correlation_id_attached(self) -> None:
        self.audit.log_login(actor=self.actor, outcome="success")
        event = self._get_last_event()
        assert event["correlation_id"] == "audit-corr-001"

    def test_service_name_attached(self) -> None:
        self.audit.log_login(actor=self.actor, outcome="success")
        event = self._get_last_event()
        assert event["service"] == "test-service"

    def test_details_redacted(self) -> None:
        self.audit.log_login(actor=self.actor, outcome="success", password="secret123")
        event = self._get_last_event()
        assert event["details"]["password"] == "***REDACTED***"

    def test_event_count_increments(self) -> None:
        assert self.audit.event_count == 0
        self.audit.log_login(actor=self.actor, outcome="success")
        assert self.audit.event_count == 1
        self.audit.log_login(actor=self.actor, outcome="failure")
        assert self.audit.event_count == 2

    def test_last_event_timestamp_updated(self) -> None:
        assert self.audit.last_event_timestamp is None
        self.audit.log_login(actor=self.actor, outcome="success")
        assert self.audit.last_event_timestamp is not None
        assert "T" in self.audit.last_event_timestamp

    def test_log_privileged_generates_enhanced_event(self) -> None:
        target = Target(type="config", id="cfg-1", name="defaults.yaml")
        self.audit.log_privileged(
            actor=self.actor,
            action="set_log_level",
            target=target,
            outcome="success",
            command_text="set log level debug",
            prior_value="INFO",
            new_value="DEBUG",
        )
        event = self._get_last_event()
        assert event["event_type"] == "admin.set_log_level"
        assert event["target"]["name"] == "defaults.yaml"
        assert event["details"]["command_text"] == "set log level debug"
        assert event["details"]["prior_value"] == "INFO"
        assert event["details"]["new_value"] == "DEBUG"

    def test_sink_failure_triggers_fallback_and_health_flag(self, tmp_path: Path) -> None:
        class BrokenSink:
            def emit(self, event) -> None:
                raise RuntimeError("sink down")

            def flush(self) -> None:
                return None

            def close(self) -> None:
                return None

        audit = AuditLogger(
            redaction_engine=RedactionEngine(),
            service_name="test-service",
            sink=BrokenSink(),
        )
        audit.log_login(actor=self.actor, outcome="failure")
        assert audit.audit_sink_healthy is False
