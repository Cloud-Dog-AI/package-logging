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

"""Shared test configuration and fixtures for cloud_dog_logging tests."""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Generator

import pytest

from cloud_dog_logging.correlation import clear_correlation_id, set_service_name

_TIER_TOKENS = {"UT", "ST", "IT", "AT", "QT", "PT", "CT"}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register shared --env test option."""
    try:
        parser.addoption(
            "--env",
            action="append",
            default=[],
            help="Env tier token(s) or env file path(s); repeatable and comma-separated.",
        )
    except ValueError:
        return


def _normalise_env_files(raw: list[str] | str | None) -> list[Path]:
    values: list[str]
    if raw is None:
        values = []
    elif isinstance(raw, str):
        values = [raw]
    else:
        values = list(raw)

    tests_dir = Path(__file__).resolve().parent
    out: list[Path] = []
    for value in values:
        for part in value.split(","):
            token = part.strip()
            if not token:
                continue
            upper = token.upper()
            if upper in _TIER_TOKENS:
                tier_file = tests_dir / f"env-{upper}"
                if tier_file.is_file():
                    out.append(tier_file)
            else:
                out.append(Path(token))
    return out


def _load_env_file(path: Path, *, locked: set[str]) -> dict[str, str]:
    if not path.is_file():
        raise pytest.UsageError(f"Env file not found: {path}")
    loaded: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise pytest.UsageError(f"Invalid env line in {path}: {raw_line}")
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            raise pytest.UsageError(f"Invalid env line in {path}: {raw_line}")
        if key in locked:
            continue
        loaded[key] = value.strip()
    return loaded


@pytest.fixture(scope="session", autouse=True)
def _require_and_load_env(request: pytest.FixtureRequest) -> None:
    """Require --env and load env files before suite execution."""
    env_files = _normalise_env_files(request.config.getoption("env"))
    if not env_files:
        raise pytest.UsageError("Missing required --env argument (for example: --env UT).")
    locked = set(os.environ.keys())
    merged: dict[str, str] = {}
    for env_file in env_files:
        merged.update(_load_env_file(env_file, locked=locked))
    os.environ.update(merged)


@pytest.fixture(autouse=True)
def _reset_logging_state() -> Generator[None, None, None]:
    """Reset logging state between tests to avoid cross-contamination."""
    import cloud_dog_logging

    # Reset module-level state
    cloud_dog_logging._audit_logger = None
    cloud_dog_logging._redaction_engine = None
    cloud_dog_logging._log_config = None
    cloud_dog_logging._sampling_filter = None
    cloud_dog_logging._is_configured = False

    clear_correlation_id()
    set_service_name("test-service")

    yield

    # Clean up handlers on root logger
    root = logging.getLogger()
    root.handlers.clear()

    audit = logging.getLogger("cloud_dog_logging.audit")
    audit.handlers.clear()

    clear_correlation_id()


@pytest.fixture
def tmp_log_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def service_name() -> str:
    """Return the test service name from env or default."""
    return os.environ.get("SERVICE_NAME", "test-service")


@pytest.fixture
def log_level() -> str:
    """Return the test log level from env or default."""
    return os.environ.get("LOG_LEVEL", "DEBUG")


@pytest.fixture
def log_format() -> str:
    """Return the test log format from env or default."""
    return os.environ.get("LOG_FORMAT", "json")
