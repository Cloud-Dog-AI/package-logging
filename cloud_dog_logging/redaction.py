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

# cloud_dog_logging — Secret and PII redaction engine
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Pattern-based redaction of secrets and PII from log data.
#   Supports recursive dict/list scanning with configurable patterns.
# Related requirements: FR1.6, FR1.13, CS1.1, CS1.4
# Related architecture: CC1.5

"""Secret and PII redaction engine for cloud_dog_logging."""

from __future__ import annotations

import copy
import re
from typing import Any

from cloud_dog_logging.presets import RedactionPreset

REDACTED_VALUE = "***REDACTED***"

DEFAULT_SECRET_PATTERNS: list[str] = [
    "secret",
    "password",
    "passwd",
    "key",
    "token",
    "credential",
    "api_key",
    "apikey",
    "authorization",
    "auth",
]

DEFAULT_PII_PATTERNS: list[str] = [
    "email",
    "phone",
    "address",
    "postcode",
    "zip_code",
    "national_insurance",
    "social_security",
    "date_of_birth",
    "dob",
]


class RedactionEngine:
    """Redact secrets and PII from log data.

    Scans dict keys and string values for patterns that indicate sensitive
    information, replacing matched values with a redaction marker.

    Args:
        secret_patterns: Key name patterns indicating secrets. Defaults to
            standard patterns (password, key, token, secret, credential, etc.).
        pii_patterns: Key name patterns indicating PII. Defaults to standard
            PII patterns (email, phone, address, etc.).
        pii_enabled: Whether PII redaction is active. Defaults to True.
        additional_patterns: Extra patterns to add to the secret list.

    Related tests: UT1.3_RedactionEngine, UT1.11_SecretScanGuard
    """

    def __init__(
        self,
        secret_patterns: list[str] | None = None,
        pii_patterns: list[str] | None = None,
        pii_enabled: bool = True,
        additional_patterns: list[str] | None = None,
        presets: list[RedactionPreset] | None = None,
    ) -> None:
        base_secret = secret_patterns if secret_patterns is not None else list(DEFAULT_SECRET_PATTERNS)
        if presets:
            for preset in presets:
                base_secret.extend(preset.patterns)
        if additional_patterns:
            base_secret.extend(additional_patterns)
        self._secret_patterns = _dedupe_preserve_order(base_secret)
        self._pii_patterns = pii_patterns if pii_patterns is not None else list(DEFAULT_PII_PATTERNS)
        self._pii_enabled = pii_enabled
        self._compiled_secret = re.compile(
            "|".join(re.escape(p) for p in self._secret_patterns),
            re.IGNORECASE,
        )
        if self._pii_enabled and self._pii_patterns:
            self._compiled_pii = re.compile(
                "|".join(re.escape(p) for p in self._pii_patterns),
                re.IGNORECASE,
            )
        else:
            self._compiled_pii = None

    def _is_sensitive_key(self, key: str) -> bool:
        """Check whether a key name matches any sensitive pattern.

        Args:
            key: The key name to check.

        Returns:
            True if the key matches a secret or PII pattern.
        """
        if self._compiled_secret.search(key):
            return True
        if self._compiled_pii is not None and self._compiled_pii.search(key):
            return True
        return False

    def redact(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact secret and PII values from a dictionary.

        Performs a deep copy so the original data is not modified. Recursively
        scans nested dicts and lists.

        Args:
            data: The dictionary to redact.

        Returns:
            A new dictionary with sensitive values replaced by REDACTED_VALUE.

        Related tests: UT1.3_RedactionEngine
        """
        return self._redact_value(copy.deepcopy(data))  # type: ignore[return-value]

    def redact_string(self, value: str) -> str:
        """Redact potential secrets embedded in a string value.

        Looks for patterns like ``key=value`` or ``"key": "value"`` and
        redacts the value portion if the key matches a sensitive pattern.

        Args:
            value: The string to scan and redact.

        Returns:
            The string with sensitive values replaced.

        Related tests: UT1.3_RedactionEngine
        """

        # Pattern: key=value or key="value" or "key": "value"
        def _replace(match: re.Match[str]) -> str:
            key = match.group(1)
            if self._is_sensitive_key(key):
                sep = match.group(2)
                return f"{key}{sep}{REDACTED_VALUE}"
            return match.group(0)

        # Match key=value patterns (both quoted and unquoted)
        pattern = r'(["\']?[\w]+["\']?)([\s]*[=:]\s*)["\']?[^"\',\s}]+["\']?'
        return re.sub(pattern, _replace, value)

    def _redact_value(self, value: Any, key: str | None = None) -> Any:
        """Recursively redact sensitive values.

        Args:
            value: The value to process.
            key: The parent key name, used for pattern matching.

        Returns:
            The redacted value.
        """
        if key is not None and self._is_sensitive_key(key):
            return REDACTED_VALUE

        if isinstance(value, dict):
            return {k: self._redact_value(v, key=k) for k, v in value.items()}

        if isinstance(value, list):
            return [self._redact_value(item) for item in value]

        return value

    @property
    def secret_patterns(self) -> list[str]:
        """Return the current list of secret patterns."""
        return list(self._secret_patterns)

    @property
    def pii_patterns(self) -> list[str]:
        """Return the current list of PII patterns."""
        return list(self._pii_patterns)


def _dedupe_preserve_order(patterns: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for pattern in patterns:
        key = pattern.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(pattern)
    return ordered
