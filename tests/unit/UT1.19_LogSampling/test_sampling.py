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

"""UT1.19: DEBUG log sampling filter tests."""

from __future__ import annotations

import logging

from cloud_dog_logging.sampling import SamplingFilter


def _record(name: str, level: int) -> logging.LogRecord:
    return logging.makeLogRecord({"name": name, "levelno": level, "msg": "m", "args": (), "exc_info": None})


class TestLogSampling:
    def test_rate_zero_drops_all_debug(self) -> None:
        filt = SamplingFilter({"httpx": 0.0}, seed=1)
        assert filt.filter(_record("httpx", logging.DEBUG)) is False
        assert filt.sampled_out_count == 1

    def test_rate_one_keeps_all_debug(self) -> None:
        filt = SamplingFilter({"httpx": 1.0}, seed=1)
        assert filt.filter(_record("httpx", logging.DEBUG)) is True
        assert filt.sampled_out_count == 0

    def test_warning_and_error_always_pass(self) -> None:
        filt = SamplingFilter({"httpx": 0.0}, seed=1)
        assert filt.filter(_record("httpx", logging.WARNING)) is True
        assert filt.filter(_record("httpx", logging.ERROR)) is True

    def test_hierarchical_lookup(self) -> None:
        filt = SamplingFilter({"httpx": 0.0}, seed=1)
        assert filt.filter(_record("httpx.client.transport", logging.DEBUG)) is False
