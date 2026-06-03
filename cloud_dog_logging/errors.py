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

# cloud_dog_logging — Logging-specific exceptions
#
# Licence: Proprietary — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Custom exception classes for the logging package.
# Related requirements: FR1.1, FR1.2
# Related architecture: SA1

"""Logging-specific exceptions for cloud_dog_logging."""


class LoggingConfigError(Exception):
    """Raised when logging configuration is invalid or incomplete."""


class AuditEventError(Exception):
    """Raised when an audit event fails validation."""


class RedactionError(Exception):
    """Raised when redaction processing encounters an error."""
