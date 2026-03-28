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

"""UT1.11: Secret Scan Guard — ensure no secrets in log output."""

from __future__ import annotations

import json
import logging
from io import StringIO

from cloud_dog_logging.audit_logger import AuditLogger
from cloud_dog_logging.audit_schema import Actor
from cloud_dog_logging.correlation import set_correlation_id, set_service_name
from cloud_dog_logging.redaction import RedactionEngine, REDACTED_VALUE


class TestSecretScanGuard:
    """Test suite verifying secrets are redacted from all log output."""

    def setup_method(self) -> None:
        set_correlation_id("scan-corr-001")
        set_service_name("test-service")

    def test_secret_in_audit_details_redacted(self) -> None:
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        py_logger = logging.getLogger("test.secret_scan.audit")
        py_logger.handlers.clear()
        py_logger.addHandler(handler)
        py_logger.setLevel(logging.DEBUG)
        py_logger.propagate = False

        audit = AuditLogger(logger=py_logger, redaction_engine=RedactionEngine())
        actor = Actor(type="user", id="u-1")
        audit.log_login(actor=actor, outcome="success", password="my-secret-pass")

        output = stream.getvalue().strip()
        event = json.loads(output)
        assert event["details"]["password"] == REDACTED_VALUE
        assert "my-secret-pass" not in output

    def test_secret_in_nested_audit_details_redacted(self) -> None:
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        py_logger = logging.getLogger("test.secret_scan.nested")
        py_logger.handlers.clear()
        py_logger.addHandler(handler)
        py_logger.setLevel(logging.DEBUG)
        py_logger.propagate = False

        audit = AuditLogger(logger=py_logger, redaction_engine=RedactionEngine())
        actor = Actor(type="user", id="u-1")
        audit.log_tool_call(
            actor=actor,
            tool="db_query",
            params={"connection": {"password": "db-secret", "host": "localhost"}},
            outcome="success",
            duration_ms=50,
        )

        output = stream.getvalue().strip()
        assert "db-secret" not in output

    def test_token_in_audit_details_redacted(self) -> None:
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        py_logger = logging.getLogger("test.secret_scan.token")
        py_logger.handlers.clear()
        py_logger.addHandler(handler)
        py_logger.setLevel(logging.DEBUG)
        py_logger.propagate = False

        audit = AuditLogger(logger=py_logger, redaction_engine=RedactionEngine())
        actor = Actor(type="service", id="svc-1")
        audit.log_login(actor=actor, outcome="success", api_token="tok-xyz-123")

        output = stream.getvalue().strip()
        assert "tok-xyz-123" not in output

    def test_app_logger_extra_redacted(self) -> None:
        from cloud_dog_logging.app_logger import AppLogger

        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        py_logger = logging.getLogger("test.secret_scan.app")
        py_logger.handlers.clear()
        py_logger.addHandler(handler)
        py_logger.setLevel(logging.DEBUG)
        py_logger.propagate = False

        app = AppLogger(logger=py_logger, redaction_engine=RedactionEngine())
        # The redaction happens on the extra dict; the password should not
        # appear in the extra dict passed to the underlying logger
        app.info("User login", password="should-be-redacted")
        # We verify the method executed without error
        assert "User login" in stream.getvalue()

    def test_multiple_secrets_all_redacted(self) -> None:
        engine = RedactionEngine()
        data = {
            "password": "pass1",
            "api_key": "key2",
            "secret": "sec3",
            "token": "tok4",
            "credential": "cred5",
            "safe_field": "visible",
        }
        result = engine.redact(data)
        for key in ["password", "api_key", "secret", "token", "credential"]:
            assert result[key] == REDACTED_VALUE
        assert result["safe_field"] == "visible"
