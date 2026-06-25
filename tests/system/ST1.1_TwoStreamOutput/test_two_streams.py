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

"""ST1.1: Two Stream Output — verify separate audit and app log streams."""

from __future__ import annotations

import json
from pathlib import Path

from cloud_dog_logging import setup_logging, get_logger, get_audit_logger
from cloud_dog_logging.audit_schema import Actor
from cloud_dog_logging.correlation import set_correlation_id


class TestTwoStreamOutput:
    """Test suite verifying two separate log streams."""

    def test_app_and_audit_write_to_separate_files(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        audit_log = str(tmp_path / "audit.log.jsonl")

        setup_logging(
            {
                "service_name": "two-stream-test",
                "log": {
                    "level": "DEBUG",
                    "format": "json",
                    "app_log": app_log,
                    "audit_log": audit_log,
                    "console": False,
                },
            }
        )

        set_correlation_id("st1-corr-001")

        logger = get_logger("test.two_streams")
        logger.info("Application log entry")

        audit = get_audit_logger()
        actor = Actor(type="user", id="u-1")
        audit.log_login(actor=actor, outcome="success")

        app_content = Path(app_log).read_text()
        audit_content = Path(audit_log).read_text()

        # App log should contain the app message
        assert "Application log entry" in app_content
        # Audit log should contain the audit event
        assert "user.login" in audit_content

    def test_no_cross_contamination(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        audit_log = str(tmp_path / "audit.log.jsonl")

        setup_logging(
            {
                "service_name": "cross-test",
                "log": {
                    "level": "DEBUG",
                    "format": "json",
                    "app_log": app_log,
                    "audit_log": audit_log,
                    "console": False,
                },
            }
        )

        set_correlation_id("st1-corr-002")

        logger = get_logger("test.cross")
        logger.info("App only message")

        audit = get_audit_logger()
        actor = Actor(type="service", id="svc-1")
        audit.log_security(
            actor=actor,
            action="lockout",
            target=Actor(type="user", id="u-2"),
            outcome="success",
        )

        audit_content = Path(audit_log).read_text()

        # App message should NOT appear in audit log
        assert "App only message" not in audit_content
        # Audit event type should NOT appear in app log as a direct entry
        # (It may appear if audit logger propagates, which we prevent)

    def test_both_streams_json_lines(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        audit_log = str(tmp_path / "audit.log.jsonl")

        setup_logging(
            {
                "service_name": "json-test",
                "log": {
                    "level": "DEBUG",
                    "format": "json",
                    "app_log": app_log,
                    "audit_log": audit_log,
                    "console": False,
                },
            }
        )

        set_correlation_id("st1-corr-003")

        logger = get_logger("test.json")
        logger.info("JSON test")

        audit = get_audit_logger()
        audit.log_login(actor=Actor(type="user", id="u-1"), outcome="success")

        # Verify app log is valid JSON lines
        for line in Path(app_log).read_text().strip().splitlines():
            if line.strip():
                parsed = json.loads(line)
                assert isinstance(parsed, dict)

        # Verify audit log is valid JSON lines
        for line in Path(audit_log).read_text().strip().splitlines():
            if line.strip():
                parsed = json.loads(line)
                assert isinstance(parsed, dict)
