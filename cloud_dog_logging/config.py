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

# cloud_dog_logging — Log configuration from platform config (PS-80)
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Configuration reader for log settings. Reads from platform
#   config (cloud_dog_config) if available, otherwise falls back to dict-based
#   configuration or sensible defaults.
# Related requirements: FR1.11, FR1.16
# Related architecture: CC1.1

"""Log configuration reader for cloud_dog_logging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LogConfig:
    """Logging configuration with sensible defaults.

    All settings can be overridden via the platform config system (PS-80)
    or by passing a dict to ``from_dict()``.

    Attributes:
        service_name: The service name for log entries.
        log_level: Global log level. Defaults to ``INFO``.
        log_format: Output format (``json`` or ``text``). Defaults to ``json``.
        app_log_file: Path to the application log file. None for stdout-only.
        audit_log_file: Path to the audit log file. None for stdout-only.
        console_output: Whether to also log to stdout. Defaults to True.
        rotation_max_bytes: Max file size before rotation. Defaults to 10 MB.
        rotation_backup_count: Number of rotated files to retain. Defaults to 5.
        redaction_patterns: Additional secret patterns for redaction.
        pii_redaction: Whether PII redaction is enabled. Defaults to True.
        level_overrides: Per-logger level overrides (e.g., sqlalchemy=WARNING).

    Related tests: ST1.4_LogLevelConfig, AT1.1_ServiceStartupPattern
    """

    service_name: str = "unknown"
    service_instance: str = "unknown"
    environment: str = "unknown"
    log_level: str = "INFO"
    log_format: str = "json"
    app_log_file: str | None = None
    audit_log_file: str | None = None
    console_output: bool = True
    rotation_max_bytes: int = 10_485_760
    rotation_backup_count: int = 5
    rotation_mode: str = "size"
    rotation_when: str = "midnight"
    rotation_interval: int = 1
    rotation_compress: bool = True
    integrity_enabled: bool = True
    integrity_interval_seconds: int = 300
    integrity_log_file: str = "logs/audit-integrity.log"
    integrity_hash_algorithm: str = "sha256"
    retention_hot_days: int = 60
    retention_cold_days: int = 365
    retention_archive_format: str = "gz"
    redaction_patterns: list[str] = field(default_factory=list)
    redaction_presets: list[str] = field(default_factory=lambda: ["default"])
    pii_redaction: bool = True
    level_overrides: dict[str, str] = field(default_factory=dict)
    sampling_rates: dict[str, float] = field(default_factory=dict)
    audit_signing_enabled: bool = False
    audit_signing_key: str | None = None

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> LogConfig:
        """Create a LogConfig from a dictionary.

        Reads values from the ``log.*`` namespace. Missing values use defaults.

        Args:
            config: A dictionary (typically from GlobalConfig or a plain dict).

        Returns:
            A populated LogConfig instance.

        Related tests: AT1.1_ServiceStartupPattern
        """
        log_section = config.get("log", {})
        if not isinstance(log_section, dict):
            log_section = {}

        redaction_section = log_section.get("redaction", {})
        if not isinstance(redaction_section, dict):
            redaction_section = {}

        audit_section = log_section.get("audit", {})
        if not isinstance(audit_section, dict):
            audit_section = {}
        rotation_section = log_section.get("rotation", {})
        if not isinstance(rotation_section, dict):
            rotation_section = {}
        integrity_section = log_section.get("integrity", {})
        if not isinstance(integrity_section, dict):
            integrity_section = {}
        retention_section = log_section.get("retention", {})
        if not isinstance(retention_section, dict):
            retention_section = {}
        signing_section = audit_section.get("signing", log_section.get("signing", {}))
        if not isinstance(signing_section, dict):
            signing_section = {}

        redaction_patterns = redaction_section.get("patterns", log_section.get("redaction_patterns", []))
        if isinstance(redaction_patterns, str):
            redaction_patterns = [redaction_patterns]
        elif not isinstance(redaction_patterns, list):
            redaction_patterns = []

        redaction_presets = redaction_section.get("presets", log_section.get("redaction_presets", ["default"]))
        if isinstance(redaction_presets, str):
            redaction_presets = [redaction_presets]
        elif not isinstance(redaction_presets, list):
            redaction_presets = ["default"]

        sampling_rates = log_section.get("sampling", {})
        if not isinstance(sampling_rates, dict):
            sampling_rates = {}

        return cls(
            service_name=config.get("service_name", config.get("app_name", "unknown")),
            service_instance=log_section.get("service_instance", config.get("service_instance", "unknown")),
            environment=log_section.get("environment", config.get("environment", "unknown")),
            log_level=log_section.get("level", "INFO"),
            log_format=log_section.get("format", "json"),
            app_log_file=log_section.get("app_log", None),
            audit_log_file=log_section.get("audit_log", None),
            console_output=log_section.get("console", True),
            rotation_max_bytes=rotation_section.get("max_bytes", log_section.get("rotation_max_bytes", 10_485_760)),
            rotation_backup_count=rotation_section.get("backup_count", log_section.get("rotation_backup_count", 5)),
            rotation_mode=rotation_section.get("mode", "size"),
            rotation_when=rotation_section.get("when", "midnight"),
            rotation_interval=rotation_section.get("interval", 1),
            rotation_compress=bool(rotation_section.get("compress", True)),
            integrity_enabled=bool(integrity_section.get("enabled", True)),
            integrity_interval_seconds=int(integrity_section.get("interval_seconds", 300)),
            integrity_log_file=integrity_section.get("log_file", "logs/audit-integrity.log"),
            integrity_hash_algorithm=integrity_section.get("hash_algorithm", "sha256"),
            retention_hot_days=int(retention_section.get("hot_days", 60)),
            retention_cold_days=int(retention_section.get("cold_days", 365)),
            retention_archive_format=retention_section.get("archive_format", "gz"),
            redaction_patterns=redaction_patterns,
            redaction_presets=redaction_presets,
            pii_redaction=redaction_section.get("pii_redaction", log_section.get("pii_redaction", True)),
            level_overrides=log_section.get("levels", {}),
            sampling_rates=sampling_rates,
            audit_signing_enabled=bool(signing_section.get("enabled", False)),
            audit_signing_key=signing_section.get("key"),
        )

    @classmethod
    def from_platform_config(cls, platform_config: Any) -> LogConfig:
        """Create a LogConfig from a platform config object (cloud_dog_config).

        Attempts to use the ``get()`` method of GlobalConfig. Falls back to
        treating the object as a dict.

        Args:
            platform_config: A GlobalConfig instance or dict-like object.

        Returns:
            A populated LogConfig instance.

        Related tests: AT1.1_ServiceStartupPattern
        """
        if hasattr(platform_config, "get"):
            # Try GlobalConfig-style access
            config_dict: dict[str, Any] = {}
            try:
                log_section = platform_config.get("log", {})
                config_dict["log"] = log_section if isinstance(log_section, dict) else {}
            except Exception:
                config_dict["log"] = {}

            try:
                config_dict["service_name"] = platform_config.get(
                    "service_name", platform_config.get("app_name", "unknown")
                )
            except Exception:
                config_dict["service_name"] = "unknown"
            try:
                config_dict["service_instance"] = platform_config.get("service_instance", "unknown")
            except Exception:
                config_dict["service_instance"] = "unknown"
            try:
                config_dict["environment"] = platform_config.get("environment", "unknown")
            except Exception:
                config_dict["environment"] = "unknown"

            return cls.from_dict(config_dict)

        if isinstance(platform_config, dict):
            return cls.from_dict(platform_config)

        return cls()
