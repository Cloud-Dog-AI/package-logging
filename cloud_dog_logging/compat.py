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

# cloud_dog_logging — Backward-compatible setup_logger() function
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Drop-in replacement for the setup_logger() function used in
#   existing projects (notification-agent, expert-agent). Returns a stdlib
#   Logger configured with the specified format, level, and handlers.
# Related requirements: FR1.17
# Related architecture: CC1.9

"""Backward-compatible setup_logger() for cloud_dog_logging."""

from __future__ import annotations

import logging

from cloud_dog_logging.formatters.json_formatter import JSONFormatter
from cloud_dog_logging.formatters.text_formatter import TextFormatter
from cloud_dog_logging.handlers.rotating_file import ConfigurableRotatingHandler
from cloud_dog_logging.handlers.stdout_handler import StdoutHandler


def setup_logger(
    name: str,
    log_file: str,
    log_level: str = "INFO",
    log_format: str = "json",
    console: bool = True,
) -> logging.Logger:
    """Create and configure a logger compatible with existing project patterns.

    This is a drop-in replacement for the ``setup_logger()`` function used in
    notification-agent and expert-agent. It returns a standard Python logger
    configured with the specified format, level, and output handlers.

    Args:
        name: The logger name (typically ``__name__``).
        log_file: Path to the log file.
        log_level: The log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            Defaults to ``INFO``.
        log_format: Output format — ``json`` for structured JSON Lines or
            ``text`` for human-readable. Defaults to ``json``.
        console: Whether to also output to stdout. Defaults to True.

    Returns:
        A configured ``logging.Logger`` instance.

    Related tests: UT1.10_BackwardCompat
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicates on re-init
    logger.handlers.clear()

    # Select formatter
    if log_format.lower() == "json":
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # File handler
    file_handler = ConfigurableRotatingHandler(
        filename=log_file,
        max_bytes=10_485_760,  # 10 MB
        backup_count=5,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    if console:
        console_handler = StdoutHandler(stream_name="stdout")
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger
