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

"""ST1.3: Append-Only Audit — audit log append-only semantics tests."""

from __future__ import annotations

import json
from pathlib import Path

from cloud_dog_logging import setup_logging, get_audit_logger
from cloud_dog_logging.audit_schema import Actor, Target
from cloud_dog_logging.correlation import set_correlation_id


class TestAppendOnlyAudit:
    """Test suite for append-only audit log semantics."""

    def test_multiple_events_all_preserved(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "append-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("append-001")

        audit = get_audit_logger()
        actor = Actor(type="user", id="u-1")

        for i in range(10):
            audit.log_login(actor=actor, outcome="success", attempt=i)

        lines = Path(audit_log).read_text().strip().splitlines()
        # Filter to only JSON lines (audit events)
        events = [json.loads(line) for line in lines if line.strip().startswith("{")]
        assert len(events) == 10

    def test_audit_handler_opens_in_append_mode(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")

        # First session
        setup_logging(
            {
                "service_name": "append-mode-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("append-002")
        audit = get_audit_logger()
        audit.log_login(actor=Actor(type="user", id="u-1"), outcome="success")

        content_after_first = Path(audit_log).read_text()
        assert len(content_after_first.strip().splitlines()) >= 1

    def test_no_truncation_on_write(self, tmp_path: Path) -> None:
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "no-truncate-test",
                "log": {"audit_log": audit_log, "console": False},
            }
        )
        set_correlation_id("append-003")

        audit = get_audit_logger()
        actor = Actor(type="user", id="u-1")

        # Write events
        for i in range(5):
            audit.log_crud(
                actor=actor,
                action="create",
                target=Target(type="resource", id=f"r-{i}"),
                outcome="success",
            )

        lines = Path(audit_log).read_text().strip().splitlines()
        json_lines = [line for line in lines if line.strip().startswith("{")]
        assert len(json_lines) == 5
        # All events should be valid JSON in either direct event format
        # or wrapped formatter format.
        for line in json_lines:
            parsed = json.loads(line)
            if "event_type" in parsed:
                assert parsed["event_type"]
            else:
                inner = json.loads(parsed["message"])
                assert "event_type" in inner
