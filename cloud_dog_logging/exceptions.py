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

# cloud_dog_logging — Structured exception serialisation
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Standard utility to serialise exceptions with stable stack hash.
# Related requirements: FR1.24
# Related architecture: CC1.17

"""Structured exception serialisation helpers."""

from __future__ import annotations

import hashlib
import traceback


def format_exception(exc: BaseException) -> dict[str, object]:
    """Serialise an exception with type, message, traceback, and stack hash."""
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    frames = traceback.extract_tb(exc.__traceback__)
    frame_signature = "|".join(f"{frame.filename}:{frame.name}:{(frame.line or '').strip()}" for frame in frames)
    normalised = f"{exc.__class__.__name__}:{str(exc)}:{frame_signature}"
    stack_hash = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
    return {
        "type": exc.__class__.__name__,
        "message": str(exc),
        "stack_hash": stack_hash,
        "traceback": [line.rstrip("\n") for line in tb_lines],
    }
