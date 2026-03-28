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

# cloud_dog_logging — Public API
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Drop-in Python logging library implementing PS-40. Provides
#   two mandatory log streams (audit + application), structured JSON output,
#   correlation ID propagation, secret redaction, and configurable rotation.
# Related requirements: FR1.1, FR1.9, FR1.18, FR1.19, FR1.20, FR1.21, FR1.22, FR1.23, FR1.24
# Related architecture: SA1, CC1.1

"""cloud_dog_logging — PS-40 Logging & Observability for Cloud-Dog services."""

from __future__ import annotations

import atexit
import logging
from typing import Any, Callable

from cloud_dog_logging.app_logger import AppLogger
from cloud_dog_logging.audit_logger import AuditLogger
from cloud_dog_logging.audit_schema import Actor, AuditEvent, Target
from cloud_dog_logging.batching import BatchingSink
from cloud_dog_logging.compat import setup_logger
from cloud_dog_logging.config import LogConfig
from cloud_dog_logging.correlation import (
    clear_correlation_id,
    get_correlation_id,
    get_environment,
    get_service_name,
    get_service_instance,
    set_correlation_id,
    set_environment,
    set_service_name,
    set_service_instance,
)
from cloud_dog_logging.exceptions import format_exception
from cloud_dog_logging.formatters.json_formatter import JSONFormatter
from cloud_dog_logging.formatters.text_formatter import TextFormatter
from cloud_dog_logging.handlers.dual_handler import DualHandler
from cloud_dog_logging.handlers.rotating_file import ConfigurableRotatingHandler
from cloud_dog_logging.handlers.stdout_handler import StdoutHandler
from cloud_dog_logging.health.reporter import LogHealthReporter
from cloud_dog_logging.integrity import AuditIntegrityVerifier
from cloud_dog_logging.presets import BUILTIN_PRESETS, RedactionPreset, load_presets
from cloud_dog_logging.redaction import RedactionEngine
from cloud_dog_logging.sampling import SamplingFilter
from cloud_dog_logging.signing import HMACSigner
from cloud_dog_logging.sinks import AuditSink, DatabaseSink, FanOutSink, FileSink, StdoutSink
from cloud_dog_logging.tool_events import log_tool_event

__all__ = [
    "setup_logging",
    "get_logger",
    "get_audit_logger",
    "setup_logger",
    "log_tool_event",
    "AppLogger",
    "AuditLogger",
    "Actor",
    "AuditEvent",
    "Target",
    "LogConfig",
    "RedactionEngine",
    "RedactionPreset",
    "BUILTIN_PRESETS",
    "load_presets",
    "SamplingFilter",
    "BatchingSink",
    "HMACSigner",
    "AuditSink",
    "FileSink",
    "StdoutSink",
    "DatabaseSink",
    "FanOutSink",
    "format_exception",
    "JSONFormatter",
    "TextFormatter",
    "ConfigurableRotatingHandler",
    "StdoutHandler",
    "DualHandler",
    "LogHealthReporter",
    "AuditIntegrityVerifier",
    "get_integrity_verifier",
    "get_correlation_id",
    "set_correlation_id",
    "clear_correlation_id",
    "get_service_name",
    "get_service_instance",
    "get_environment",
    "set_service_name",
    "set_service_instance",
    "set_environment",
]

_audit_logger: AuditLogger | None = None
_redaction_engine: RedactionEngine | None = None
_log_config: LogConfig | None = None
_sampling_filter: SamplingFilter | None = None
_integrity_verifier: AuditIntegrityVerifier | None = None
_is_configured: bool = False


def setup_logging(config: dict[str, Any] | Any | None = None) -> None:
    """One-time logging setup from config dict or platform GlobalConfig."""
    global _audit_logger, _redaction_engine, _log_config, _sampling_filter, _integrity_verifier, _is_configured

    if _audit_logger is not None:
        try:
            _audit_logger.close()
        except Exception:
            pass
    if _integrity_verifier is not None:
        try:
            _integrity_verifier.stop()
        except Exception:
            pass
        _integrity_verifier = None

    if config is None:
        _log_config = LogConfig()
    elif isinstance(config, dict):
        _log_config = LogConfig.from_dict(config)
    else:
        _log_config = LogConfig.from_platform_config(config)

    set_service_name(_log_config.service_name)
    set_service_instance(_log_config.service_instance)
    set_environment(_log_config.environment)

    presets = _resolve_redaction_presets(config, _log_config)
    _redaction_engine = RedactionEngine(
        additional_patterns=_log_config.redaction_patterns if _log_config.redaction_patterns else None,
        pii_enabled=_log_config.pii_redaction,
        presets=presets,
    )

    if _log_config.log_format.lower() == "json":
        formatter: logging.Formatter = JSONFormatter(service_name=_log_config.service_name)
    else:
        formatter = TextFormatter(service_name=_log_config.service_name)

    root_level = getattr(logging, _log_config.log_level.upper(), logging.INFO)
    app_root = logging.getLogger()
    app_root.setLevel(root_level)
    app_root.handlers.clear()

    if _log_config.app_log_file:
        file_handler = ConfigurableRotatingHandler(
            filename=_log_config.app_log_file,
            max_bytes=_log_config.rotation_max_bytes,
            backup_count=_log_config.rotation_backup_count,
            rotation_mode=_log_config.rotation_mode,
            when=_log_config.rotation_when,
            interval=_log_config.rotation_interval,
            compress=_log_config.rotation_compress,
            stream_name="application",
        )
        file_handler.setFormatter(formatter)
        if _log_config.console_output:
            stdout_handler = StdoutHandler(stream_name="stdout")
            stdout_handler.setFormatter(formatter)
            dual = DualHandler(file_handler=file_handler, stream_handler=stdout_handler)
            dual.setFormatter(formatter)
            app_root.addHandler(dual)
        else:
            app_root.addHandler(file_handler)
    elif _log_config.console_output:
        stdout_handler = StdoutHandler(stream_name="stdout")
        stdout_handler.setFormatter(formatter)
        app_root.addHandler(stdout_handler)

    _sampling_filter = None
    if _log_config.sampling_rates:
        _sampling_filter = SamplingFilter(_log_config.sampling_rates)
        for handler in app_root.handlers:
            handler.addFilter(_sampling_filter)

    audit_sink = _build_audit_sink(_log_config, on_audit_rotate=_on_audit_rotation)
    signer = _build_signer(_log_config)
    audit_py_logger = logging.getLogger("cloud_dog_logging.audit")
    audit_py_logger.setLevel(logging.INFO)
    audit_py_logger.propagate = False
    if not audit_py_logger.handlers:
        audit_py_logger.addHandler(logging.NullHandler())

    _audit_logger = AuditLogger(
        logger=audit_py_logger,
        redaction_engine=_redaction_engine,
        service_name=_log_config.service_name,
        sink=audit_sink,
        signer=signer,
    )

    if _log_config.integrity_enabled:
        audit_path = _log_config.audit_log_file or "logs/audit.log.jsonl"
        _integrity_verifier = AuditIntegrityVerifier(
            audit_log_path=audit_path,
            integrity_log_path=_log_config.integrity_log_file,
            interval_seconds=_log_config.integrity_interval_seconds,
            hash_algorithm=_log_config.integrity_hash_algorithm,
            service_name=_log_config.service_name,
            service_instance=_log_config.service_instance,
        )
        _integrity_verifier.start()

    for logger_name, level_str in _log_config.level_overrides.items():
        override_level = getattr(logging, level_str.upper(), None)
        if override_level is not None:
            logging.getLogger(logger_name).setLevel(override_level)

    _is_configured = True


def get_logger(name: str, pii_redaction: bool = True) -> AppLogger:
    """Get a configured application logger for the given module name."""
    py_logger = logging.getLogger(name)

    redaction = _redaction_engine
    if redaction is None:
        redaction = RedactionEngine(pii_enabled=pii_redaction)

    return AppLogger(logger=py_logger, redaction_engine=redaction)


def get_audit_logger() -> AuditLogger:
    """Get the singleton audit logger for security events."""
    global _audit_logger
    if _audit_logger is None:
        py_logger = logging.getLogger("cloud_dog_logging.audit")
        if not py_logger.handlers:
            py_logger.addHandler(logging.NullHandler())
        _audit_logger = AuditLogger(logger=py_logger)
    return _audit_logger


def get_integrity_verifier() -> AuditIntegrityVerifier | None:
    """Get the audit integrity verifier when enabled."""
    return _integrity_verifier


def _on_audit_rotation(_meta: dict[str, object]) -> None:
    verifier = get_integrity_verifier()
    if verifier is not None:
        verifier.compute_now(trigger="rotation")


def _build_audit_sink(
    log_config: LogConfig,
    on_audit_rotate: Callable[[dict[str, object]], None] | None = None,
) -> AuditSink:
    sinks: list[AuditSink] = []
    audit_path = log_config.audit_log_file or "logs/audit.log.jsonl"
    sinks.append(
        FileSink(
            audit_path,
            max_bytes=log_config.rotation_max_bytes,
            backup_count=log_config.rotation_backup_count,
            rotation_mode=log_config.rotation_mode,
            when=log_config.rotation_when,
            interval=log_config.rotation_interval,
            compress=log_config.rotation_compress,
            on_rotate=on_audit_rotate,
        )
    )
    if log_config.console_output:
        sinks.append(StdoutSink())

    if len(sinks) == 1:
        return sinks[0]
    return FanOutSink(sinks)


def _build_signer(log_config: LogConfig) -> HMACSigner | None:
    if not log_config.audit_signing_enabled:
        return None
    return HMACSigner(log_config.audit_signing_key or "")


def _resolve_redaction_presets(config: dict[str, Any] | Any | None, log_config: LogConfig) -> list[RedactionPreset]:
    if isinstance(config, dict):
        return load_presets(config)
    return load_presets({"log": {"redaction": {"presets": log_config.redaction_presets}}})


def _shutdown_integrity_verifier() -> None:
    verifier = get_integrity_verifier()
    if verifier is not None:
        try:
            verifier.stop()
        except Exception:
            pass


atexit.register(_shutdown_integrity_verifier)
