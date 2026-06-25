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

"""AT1.5: End-to-end signed audit chain tests."""

from __future__ import annotations

import hashlib
import hmac
import json
from copy import deepcopy
from pathlib import Path

from cloud_dog_logging import get_audit_logger, setup_logging
from cloud_dog_logging.audit_schema import Actor
from cloud_dog_logging.correlation import set_correlation_id


def _verify_event_signature(event: dict, key: str) -> str:
    details = dict(event.get("details") or {})
    signature = details.pop("_signature", None)
    assert isinstance(signature, str)
    canonical = deepcopy(event)
    canonical["details"] = details
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
    expected = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    assert signature == expected
    return signature


class TestSignedAuditChain:
    def test_signed_chain_and_tamper_detection(self, tmp_path: Path) -> None:
        key = "chain-secret"
        audit_log = str(tmp_path / "audit.log.jsonl")
        setup_logging(
            {
                "service_name": "signed-audit-test",
                "log": {
                    "audit_log": audit_log,
                    "console": False,
                    "audit": {"signing": {"enabled": True, "key": key}},
                },
            }
        )

        set_correlation_id("signed-001")
        audit = get_audit_logger()
        actor = Actor(type="user", id="u-1")
        audit.log_login(actor=actor, outcome="success")
        audit.log_login(actor=actor, outcome="success")
        audit.log_login(actor=actor, outcome="success")
        audit.close()

        events = [json.loads(line) for line in Path(audit_log).read_text(encoding="utf-8").strip().splitlines()]
        assert len(events) == 3

        prev_signature: str | None = None
        for event in events:
            details = event.get("details") or {}
            if prev_signature is not None:
                assert details.get("_prev_signature") == prev_signature
            prev_signature = _verify_event_signature(event, key)

        tampered = deepcopy(events[1])
        tampered["action"] = "tampered"
        details = dict(tampered.get("details") or {})
        signature = details.get("_signature")
        assert isinstance(signature, str)

        canonical = deepcopy(tampered)
        canonical_details = dict(canonical.get("details") or {})
        canonical_details.pop("_signature", None)
        canonical["details"] = canonical_details
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
        recalculated = hmac.new(key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        assert recalculated != signature
