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

"""UT1.5: Audit Event Schema — validation tests."""

from __future__ import annotations

import pytest

from cloud_dog_logging.audit_schema import Actor, AuditEvent, Target, VALID_OUTCOMES


class TestActor:
    """Test suite for Actor dataclass."""

    def test_valid_user_actor(self) -> None:
        actor = Actor(type="user", id="u-123")
        assert actor.type == "user"
        assert actor.id == "u-123"
        assert actor.roles is None

    def test_valid_service_actor(self) -> None:
        actor = Actor(type="service", id="svc-1")
        assert actor.type == "service"

    def test_valid_system_actor(self) -> None:
        actor = Actor(type="system", id="sys-0")
        assert actor.type == "system"

    def test_actor_with_roles(self) -> None:
        actor = Actor(type="user", id="u-1", roles=["admin", "editor"])
        assert actor.roles == ["admin", "editor"]

    def test_invalid_actor_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="Actor type must be one of"):
            Actor(type="invalid", id="u-1")

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="Actor id must not be empty"):
            Actor(type="user", id="")

    def test_to_dict(self) -> None:
        actor = Actor(type="user", id="u-1", roles=["admin"])
        d = actor.to_dict()
        assert d == {"type": "user", "id": "u-1", "roles": ["admin"]}

    def test_to_dict_no_roles(self) -> None:
        actor = Actor(type="user", id="u-1")
        d = actor.to_dict()
        assert d == {"type": "user", "id": "u-1"}
        assert "roles" not in d

    def test_actor_optional_source_fields(self) -> None:
        actor = Actor(type="user", id="u-1", ip="10.0.0.1", user_agent="pytest")
        d = actor.to_dict()
        assert d["ip"] == "10.0.0.1"
        assert d["user_agent"] == "pytest"


class TestTarget:
    """Test suite for Target dataclass."""

    def test_valid_target(self) -> None:
        target = Target(type="session", id="s-1")
        assert target.type == "session"
        assert target.id == "s-1"

    def test_empty_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="Target type must not be empty"):
            Target(type="", id="t-1")

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="Target id must not be empty"):
            Target(type="user", id="")

    def test_to_dict(self) -> None:
        target = Target(type="config", id="c-1")
        assert target.to_dict() == {"type": "config", "id": "c-1"}

    def test_target_name_serialised(self) -> None:
        target = Target(type="file", id="f-1", name="rules.md")
        d = target.to_dict()
        assert d["name"] == "rules.md"


class TestAuditEvent:
    """Test suite for AuditEvent dataclass."""

    def _make_event(self, **overrides) -> AuditEvent:
        defaults = {
            "event_type": "user.login",
            "actor": Actor(type="user", id="u-1"),
            "action": "login",
            "outcome": "success",
            "correlation_id": "corr-001",
            "service": "test-service",
        }
        defaults.update(overrides)
        return AuditEvent(**defaults)

    def test_required_fields_enforced(self) -> None:
        event = self._make_event()
        assert event.event_type == "user.login"
        assert event.action == "login"
        assert event.outcome == "success"
        assert event.correlation_id == "corr-001"
        assert event.service == "test-service"
        assert event.service_instance
        assert event.environment == "unknown"
        assert event.severity == "INFO"

    def test_timestamp_auto_generated(self) -> None:
        event = self._make_event()
        assert event.timestamp.endswith("Z")
        assert "T" in event.timestamp

    def test_timestamp_explicit(self) -> None:
        event = self._make_event(timestamp="2026-01-01T00:00:00.000000Z")
        assert event.timestamp == "2026-01-01T00:00:00.000000Z"

    def test_valid_outcomes(self) -> None:
        for outcome in VALID_OUTCOMES:
            event = self._make_event(outcome=outcome)
            assert event.outcome == outcome

    def test_invalid_outcome_rejected(self) -> None:
        with pytest.raises(ValueError, match="Outcome must be one of"):
            self._make_event(outcome="unknown")

    def test_empty_event_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="event_type must not be empty"):
            self._make_event(event_type="")

    def test_empty_action_rejected(self) -> None:
        with pytest.raises(ValueError, match="action must not be empty"):
            self._make_event(action="")

    def test_empty_correlation_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="correlation_id must not be empty"):
            self._make_event(correlation_id="")

    def test_empty_service_rejected(self) -> None:
        with pytest.raises(ValueError, match="service must not be empty"):
            self._make_event(service="")

    def test_optional_target(self) -> None:
        target = Target(type="user", id="u-2")
        event = self._make_event(target=target)
        assert event.target is not None
        assert event.target.id == "u-2"

    def test_optional_details(self) -> None:
        event = self._make_event(details={"ip": "127.0.0.1"})
        assert event.details == {"ip": "127.0.0.1"}

    def test_optional_duration_ms(self) -> None:
        event = self._make_event(duration_ms=150)
        assert event.duration_ms == 150

    def test_to_dict_all_fields(self) -> None:
        target = Target(type="session", id="s-1")
        event = self._make_event(target=target, details={"method": "POST"}, duration_ms=42)
        d = event.to_dict()
        assert d["event_type"] == "user.login"
        assert d["actor"]["type"] == "user"
        assert d["target"]["type"] == "session"
        assert d["details"]["method"] == "POST"
        assert d["duration_ms"] == 42
        assert "timestamp" in d
        assert "service_instance" in d
        assert "environment" in d
        assert "severity" in d

    def test_to_dict_omits_none(self) -> None:
        event = self._make_event()
        d = event.to_dict()
        assert "target" not in d
        assert "details" not in d
        assert "duration_ms" not in d
