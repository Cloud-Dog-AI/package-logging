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

# cloud_dog_logging — Stdout/stderr handler for containerised deployments
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Handler that writes log output to stdout or stderr,
#   suitable for container and cloud-native deployments.
# Related requirements: FR1.7
# Related architecture: CC1.7

"""Stdout/stderr handler for containerised deployments."""

from __future__ import annotations

import logging
import sys


class StdoutHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Handler that writes log output to stdout or stderr.

    Suitable for containerised deployments where logs are collected
    from standard output streams.

    Args:
        stream_name: Either ``stdout`` or ``stderr``. Defaults to ``stdout``.

    Related tests: ST1.5_DualDestination
    """

    def __init__(self, stream_name: str = "stdout") -> None:
        if stream_name == "stderr":
            stream = sys.stderr
        else:
            stream = sys.stdout
        super().__init__(stream=stream)
