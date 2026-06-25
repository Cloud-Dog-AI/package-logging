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

"""UT1.16: Audit signing hook tests."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from cloud_dog_logging.audit_logger import AuditLogger
from cloud_dog_logging.audit_schema import Actor, AuditEvent
from cloud_dog_logging.signing import HMACSigner


class _CaptureSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def emit(self, event: AuditEvent) -> None:
        self.events.append(event)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class TestAuditSigning:
    def test_pre_and_post_hooks_add_signature_and_chain(self) -> None:
        signer = HMACSigner("test-secret")
        sink = _CaptureSink()
        audit = AuditLogger(sink=sink, signer=signer, service_name="sign-test")
        actor = Actor(type="user", id="u-1")

        audit.log_login(actor=actor, outcome="success")
        audit.log_login(actor=actor, outcome="success")

        first = sink.events[0].details or {}
        second = sink.events[1].details or {}
        assert "_signature" in first
        assert second.get("_prev_signature") == first.get("_signature")
        assert signer.last_signature == second.get("_signature")

    def test_signature_is_hmac_sha256(self) -> None:
        signer = HMACSigner("abc123")
        event = AuditEvent(
            event_type="user.login",
            actor=Actor(type="user", id="u-1"),
            action="login",
            outcome="success",
            correlation_id="cid-1",
            service="svc",
        )
        signed = signer.pre_persist(event)
        details = signed.details or {}
        signature = details.get("_signature")
        assert isinstance(signature, str)
        canonical = signed.to_dict()
        canonical_details = dict(canonical.get("details", {}))
        canonical_details.pop("_signature", None)
        canonical["details"] = canonical_details
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
        expected = hmac.new(b"abc123", payload.encode("utf-8"), hashlib.sha256).hexdigest()
        assert signature == expected

    def test_disabled_signing_emits_unsigned_events(self) -> None:
        sink = _CaptureSink()
        audit = AuditLogger(sink=sink, service_name="plain")
        audit.log_login(actor=Actor(type="user", id="u-1"), outcome="success")
        details = sink.events[0].details or {}
        assert "_signature" not in details

    def test_empty_key_rejected(self) -> None:
        with pytest.raises(ValueError):
            HMACSigner("")
