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

"""System tests for log rotation enforcement and configuration parsing."""

from __future__ import annotations

import logging
from pathlib import Path

from cloud_dog_logging.config import LogConfig
from cloud_dog_logging.handlers.rotating_file import ConfigurableRotatingHandler


def _logger(name: str, handler: logging.Handler) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def test_size_rotation(tmp_path: Path) -> None:
    log_file = tmp_path / "rotate-size.log"
    handler = ConfigurableRotatingHandler(
        filename=str(log_file),
        max_bytes=350,
        backup_count=2,
        rotation_mode="size",
        compress=False,
    )
    logger = _logger("test.rotation.enforcement.size", handler)

    for idx in range(80):
        logger.info("rotation-enforcement-line-%03d", idx)

    handler.close()
    assert (tmp_path / "rotate-size.log.1").exists()


def test_rotation_event_logged(tmp_path: Path, caplog) -> None:
    log_file = tmp_path / "rotate-event.log"
    handler = ConfigurableRotatingHandler(
        filename=str(log_file),
        max_bytes=320,
        backup_count=2,
        rotation_mode="size",
        compress=False,
    )
    logger = _logger("test.rotation.enforcement.event", handler)

    caplog.set_level(logging.INFO, logger="cloud_dog_logging.rotation")
    for idx in range(60):
        logger.info("rotation-event-line-%03d", idx)
    handler.close()

    assert any(rec.message == "log_rotation" for rec in caplog.records)


def test_rotation_compress(tmp_path: Path) -> None:
    log_file = tmp_path / "rotate-compress.log"
    handler = ConfigurableRotatingHandler(
        filename=str(log_file),
        max_bytes=320,
        backup_count=2,
        rotation_mode="size",
        compress=True,
    )
    logger = _logger("test.rotation.enforcement.compress", handler)

    for idx in range(60):
        logger.info("rotation-compress-line-%03d", idx)
    handler.close()

    assert (tmp_path / "rotate-compress.log.1.gz").exists()


def test_rotation_config_from_yaml() -> None:
    config = LogConfig.from_dict(
        {
            "service_name": "svc",
            "log": {
                "rotation": {
                    "mode": "both",
                    "max_bytes": 1024,
                    "backup_count": 7,
                    "when": "midnight",
                    "interval": 2,
                    "compress": True,
                }
            },
        }
    )

    assert config.rotation_mode == "both"
    assert config.rotation_max_bytes == 1024
    assert config.rotation_backup_count == 7
    assert config.rotation_when == "midnight"
    assert config.rotation_interval == 2
    assert config.rotation_compress is True
