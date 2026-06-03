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

# cloud_dog_logging — Redaction presets
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Built-in and configurable redaction pattern presets.
# Related requirements: FR1.21
# Related architecture: CC1.14

"""Composable redaction presets for log sanitisation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RedactionPreset:
    """Named redaction pattern set."""

    name: str
    patterns: list[str]


BUILTIN_PRESETS: dict[str, RedactionPreset] = {
    "default": RedactionPreset(
        name="default",
        patterns=["token", "secret", "password", "api_key", "credential"],
    ),
    "file_tools": RedactionPreset(
        name="file_tools",
        patterns=["token", "secret", "password", "api_key", "authorization"],
    ),
}


def load_presets(config: dict[str, Any] | None) -> list[RedactionPreset]:
    """Load redaction presets from a config dictionary."""
    if not config:
        return [BUILTIN_PRESETS["default"]]

    log_section = config.get("log", {})
    if not isinstance(log_section, dict):
        return [BUILTIN_PRESETS["default"]]

    redaction_section = log_section.get("redaction", {})
    names_raw: Any = None
    if isinstance(redaction_section, dict):
        names_raw = redaction_section.get("presets")
    if names_raw is None:
        names_raw = log_section.get("redaction_presets", ["default"])

    if isinstance(names_raw, str):
        names = [names_raw]
    elif isinstance(names_raw, list):
        names = [str(item) for item in names_raw]
    else:
        names = ["default"]

    presets: list[RedactionPreset] = []
    for name in names:
        preset = BUILTIN_PRESETS.get(name)
        if preset is None:
            raise ValueError(f"Unknown redaction preset: {name}")
        presets.append(preset)
    return presets
