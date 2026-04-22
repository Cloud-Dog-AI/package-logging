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

"""NIST AU-3 and AU-8 field validation tests for AuditEvent."""

from __future__ import annotations

import re

import pytest

from cloud_dog_logging.audit_schema import Actor, AuditEvent, Target


TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def _event(outcome: str = "success") -> AuditEvent:
    return AuditEvent(
        event_type="user_function",
        actor=Actor(type="user", id="u-100", roles=["reader"], ip="10.0.0.5", user_agent="pytest"),
        action="search",
        outcome=outcome,
        correlation_id="corr-au3-1",
        service="test-service",
        service_instance="test-instance-1",
        environment="test",
        severity="INFO",
        target=Target(type="dataset", id="customers", name="customer_records"),
    )


def test_audit_event_has_all_au3_elements() -> None:
    event = _event()
    payload = event.to_dict()

    # What
    assert payload["event_type"]
    assert payload["action"]

    # When
    assert TIMESTAMP_RE.match(payload["timestamp"])

    # Where
    assert payload["service"]
    assert payload["service_instance"]
    assert payload["environment"]

    # Source
    assert payload["actor"]["ip"] == "10.0.0.5"
    assert payload["actor"]["user_agent"] == "pytest"

    # Outcome
    assert payload["outcome"] == "success"

    # Identity
    assert payload["actor"]["type"] == "user"
    assert payload["actor"]["id"] == "u-100"
    assert payload["actor"]["roles"] == ["reader"]


def test_outcome_accepts_nist_values() -> None:
    for outcome in ("success", "failure", "error", "denied", "partial"):
        assert _event(outcome=outcome).outcome == outcome


def test_outcome_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="Outcome must be one of"):
        _event(outcome="accepted")


def test_target_name_included_for_file_config_ops() -> None:
    event = AuditEvent(
        event_type="config_change",
        actor=Actor(type="user", id="admin-1"),
        action="update",
        outcome="success",
        correlation_id="corr-au3-2",
        service="test-service",
        target=Target(type="config", id="log.rotation", name="defaults.yaml"),
    )
    payload = event.to_dict()
    assert payload["target"]["name"] == "defaults.yaml"


def test_service_instance_environment_and_severity_present() -> None:
    payload = _event().to_dict()
    assert payload["service_instance"] == "test-instance-1"
    assert payload["environment"] == "test"
    assert payload["severity"] == "INFO"
