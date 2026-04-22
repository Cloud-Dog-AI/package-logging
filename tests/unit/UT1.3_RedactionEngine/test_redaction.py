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

"""UT1.3: Redaction Engine — secret and PII redaction tests."""

from __future__ import annotations

from cloud_dog_logging.redaction import RedactionEngine, REDACTED_VALUE


class TestRedactionEngine:
    """Test suite for RedactionEngine."""

    def setup_method(self) -> None:
        self.engine = RedactionEngine()

    def test_password_key_redacted(self) -> None:
        data = {"username": "admin", "password": "s3cret"}
        result = self.engine.redact(data)
        assert result["username"] == "admin"
        assert result["password"] == REDACTED_VALUE

    def test_key_pattern_redacted(self) -> None:
        data = {"api_key": "abc123", "name": "test"}
        result = self.engine.redact(data)
        assert result["api_key"] == REDACTED_VALUE
        assert result["name"] == "test"

    def test_token_pattern_redacted(self) -> None:
        data = {"access_token": "tok-xyz", "type": "bearer"}
        result = self.engine.redact(data)
        assert result["access_token"] == REDACTED_VALUE
        assert result["type"] == "bearer"

    def test_secret_pattern_redacted(self) -> None:
        data = {"client_secret": "sec-abc", "client_id": "cid-1"}
        result = self.engine.redact(data)
        assert result["client_secret"] == REDACTED_VALUE
        assert result["client_id"] == "cid-1"

    def test_credential_pattern_redacted(self) -> None:
        data = {"credential": "cred-val"}
        result = self.engine.redact(data)
        assert result["credential"] == REDACTED_VALUE

    def test_nested_dict_redacted(self) -> None:
        data = {"config": {"database": {"password": "dbpass", "host": "localhost"}}}
        result = self.engine.redact(data)
        assert result["config"]["database"]["password"] == REDACTED_VALUE
        assert result["config"]["database"]["host"] == "localhost"

    def test_list_scanning(self) -> None:
        data = {"items": [{"password": "p1"}, {"password": "p2"}]}
        result = self.engine.redact(data)
        assert result["items"][0]["password"] == REDACTED_VALUE
        assert result["items"][1]["password"] == REDACTED_VALUE

    def test_original_not_modified(self) -> None:
        data = {"password": "original"}
        result = self.engine.redact(data)
        assert data["password"] == "original"
        assert result["password"] == REDACTED_VALUE

    def test_custom_patterns(self) -> None:
        engine = RedactionEngine(additional_patterns=["custom_field"])
        data = {"custom_field": "sensitive", "normal": "ok"}
        result = engine.redact(data)
        assert result["custom_field"] == REDACTED_VALUE
        assert result["normal"] == "ok"

    def test_pii_email_redacted(self) -> None:
        data = {"email": "user@example.com", "name": "Test"}
        result = self.engine.redact(data)
        assert result["email"] == REDACTED_VALUE
        assert result["name"] == "Test"

    def test_pii_phone_redacted(self) -> None:
        data = {"phone": "+441234567890"}
        result = self.engine.redact(data)
        assert result["phone"] == REDACTED_VALUE

    def test_pii_disabled(self) -> None:
        engine = RedactionEngine(pii_enabled=False)
        data = {"email": "user@example.com"}
        result = engine.redact(data)
        assert result["email"] == "user@example.com"

    def test_case_insensitive_matching(self) -> None:
        data = {"PASSWORD": "secret", "Api_Key": "key123"}
        result = self.engine.redact(data)
        assert result["PASSWORD"] == REDACTED_VALUE
        assert result["Api_Key"] == REDACTED_VALUE

    def test_authorization_pattern(self) -> None:
        data = {"authorization": "Bearer token123"}
        result = self.engine.redact(data)
        assert result["authorization"] == REDACTED_VALUE

    def test_empty_dict(self) -> None:
        result = self.engine.redact({})
        assert result == {}

    def test_non_sensitive_keys_preserved(self) -> None:
        data = {"status": "active", "count": 42, "enabled": True}
        result = self.engine.redact(data)
        assert result == data
