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

# cloud_dog_logging — DEBUG log sampling filter
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Per-logger DEBUG-level sampling filter for high-volume logs.
# Related requirements: FR1.22
# Related architecture: CC1.15

"""Per-logger DEBUG sampling filter."""

from __future__ import annotations

import logging
import random


class SamplingFilter(logging.Filter):
    """Filter DEBUG entries according to configured per-logger rates."""

    def __init__(self, rates: dict[str, float], seed: int | None = None) -> None:
        super().__init__()
        self._rates = {name: _clamp_rate(rate) for name, rate in rates.items()}
        self._rng = random.Random(seed)
        self._sampled_out = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """Handle filter."""
        if record.levelno >= logging.WARNING:
            return True
        if record.levelno != logging.DEBUG:
            return True

        rate = self._lookup_rate(record.name)
        if rate >= 1.0:
            return True
        if rate <= 0.0:
            self._sampled_out += 1
            return False

        keep = self._rng.random() < rate
        if not keep:
            self._sampled_out += 1
        return keep

    def _lookup_rate(self, logger_name: str) -> float:
        if logger_name in self._rates:
            return self._rates[logger_name]

        parts = logger_name.split(".")
        while len(parts) > 1:
            parts.pop()
            candidate = ".".join(parts)
            if candidate in self._rates:
                return self._rates[candidate]
        return self._rates.get("*", 1.0)

    @property
    def sampled_out_count(self) -> int:
        """Return number of sampled-out DEBUG entries."""
        return self._sampled_out


def _clamp_rate(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value
