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

"""UT1.18: Redaction preset composition tests."""

from __future__ import annotations

import pytest

from cloud_dog_logging.presets import BUILTIN_PRESETS, load_presets
from cloud_dog_logging.redaction import REDACTED_VALUE, RedactionEngine


class TestRedactionPresets:
    def test_default_preset_loaded_when_no_config(self) -> None:
        presets = load_presets(None)
        assert len(presets) == 1
        assert presets[0].name == "default"

    def test_file_tools_preset_masks_authorization(self) -> None:
        presets = load_presets({"log": {"redaction": {"presets": ["default", "file_tools"]}}})
        engine = RedactionEngine(presets=presets)
        out = engine.redact({"authorization": "Bearer secret", "path": "/tmp/test"})
        assert out["authorization"] == REDACTED_VALUE
        assert out["path"] == "/tmp/test"

    def test_unknown_preset_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown redaction preset"):
            load_presets({"log": {"redaction": {"presets": ["does_not_exist"]}}})

    def test_presets_are_composable(self) -> None:
        presets = [BUILTIN_PRESETS["default"], BUILTIN_PRESETS["file_tools"]]
        engine = RedactionEngine(presets=presets)
        out = engine.redact({"api_key": "x", "authorization": "y", "safe": "ok"})
        assert out["api_key"] == REDACTED_VALUE
        assert out["authorization"] == REDACTED_VALUE
        assert out["safe"] == "ok"
