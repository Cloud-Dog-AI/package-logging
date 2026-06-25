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

"""AT1.2: Audit Event Coverage — verify all critical action audit events."""

from __future__ import annotations

import json
from pathlib import Path

from cloud_dog_logging import setup_logging, get_audit_logger
from cloud_dog_logging.audit_schema import Actor, Target
from cloud_dog_logging.correlation import set_correlation_id


class TestAuditEventCoverage:
    """Test suite verifying audit events for all critical actions."""

    def setup_method(self) -> None:
        self.actor = Actor(type="user", id="u-coverage-1", roles=["admin"])

    def test_login_event(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "coverage-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("cov-001")

        audit = get_audit_logger()
        audit.log_login(actor=self.actor, outcome="success", method="api_key")

        events = self._read_events(audit_log)
        assert any(e.get("event_type") == "user.login" for e in events)

    def test_crud_create_event(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "coverage-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("cov-002")

        audit = get_audit_logger()
        target = Target(type="user", id="u-new")
        audit.log_crud(actor=self.actor, action="create", target=target, outcome="success")

        events = self._read_events(audit_log)
        assert any(e.get("event_type") == "user.create" for e in events)
        assert any(e.get("action") == "create" for e in events)

    def test_crud_update_event(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "coverage-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("cov-003")

        audit = get_audit_logger()
        target = Target(type="config", id="c-1")
        audit.log_crud(actor=self.actor, action="update", target=target, outcome="success")

        events = self._read_events(audit_log)
        assert any(e.get("action") == "update" for e in events)

    def test_crud_delete_event(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "coverage-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("cov-004")

        audit = get_audit_logger()
        target = Target(type="session", id="s-1")
        audit.log_crud(actor=self.actor, action="delete", target=target, outcome="success")

        events = self._read_events(audit_log)
        assert any(e.get("action") == "delete" for e in events)

    def test_config_change_event(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "coverage-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("cov-005")

        audit = get_audit_logger()
        audit.log_config_change(
            actor=self.actor,
            diff_summary={"changed": ["log.level"], "old": "INFO", "new": "DEBUG"},
            outcome="success",
        )

        events = self._read_events(audit_log)
        assert any(e.get("event_type") == "config.change" for e in events)

    def test_tool_call_event(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "coverage-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("cov-006")

        audit = get_audit_logger()
        audit.log_tool_call(
            actor=self.actor,
            tool="web_search",
            params={"query": "test"},
            outcome="success",
            duration_ms=250,
        )

        events = self._read_events(audit_log)
        assert any(e.get("event_type") == "tool.call" for e in events)
        assert any(e.get("duration_ms") == 250 for e in events)

    def test_security_event(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "coverage-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("cov-007")

        audit = get_audit_logger()
        target = Target(type="user", id="u-locked")
        audit.log_security(actor=self.actor, action="lockout", target=target, outcome="success")

        events = self._read_events(audit_log)
        assert any(e.get("event_type") == "security.lockout" for e in events)

    def test_all_events_have_correct_schema(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "schema-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("cov-008")

        audit = get_audit_logger()
        audit.log_login(actor=self.actor, outcome="success")
        audit.log_crud(
            actor=self.actor,
            action="create",
            target=Target(type="resource", id="r-1"),
            outcome="success",
        )
        audit.log_config_change(
            actor=self.actor,
            diff_summary={"k": "v"},
            outcome="success",
        )

        events = self._read_events(audit_log)
        required_fields = {
            "timestamp",
            "event_type",
            "actor",
            "action",
            "outcome",
            "correlation_id",
            "service",
            "service_instance",
            "component",
            "source_host",
            "source_process",
            "source_application",
            "process_id",
            "environment",
        }
        for event in events:
            for field in required_fields:
                assert field in event, f"Missing field '{field}' in event: {event}"

    @staticmethod
    def _read_events(path: str) -> list[dict]:
        content = Path(path).read_text().strip()
        events = []
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            parsed = json.loads(line)
            # The audit logger wraps the event in the JSON formatter's output.
            # The actual event is in the "message" field as a JSON string.
            if "message" in parsed:
                try:
                    inner = json.loads(parsed["message"])
                    events.append(inner)
                except (json.JSONDecodeError, TypeError):
                    events.append(parsed)
            else:
                events.append(parsed)
        return events
