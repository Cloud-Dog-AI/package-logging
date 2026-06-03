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

# cloud_dog_logging — Formatters package
#
# Licence: Apache 2.0 — Cloud-Dog AI Platform
# Owner: Cloud-Dog AI
# Description: Log formatters for JSON Lines and human-readable output, plus
#   the public ``add_json_field`` registry for declaring additional top-level
#   JSON-output fields without subclassing or monkey-patching ``JSONFormatter``.
# Related architecture: SA1, CC1.6

"""Log formatters for cloud_dog_logging.

Public surface:

- :class:`JSONFormatter` — structured JSON Lines output with stable schema.
- :class:`TextFormatter` — human-readable text output.
- :func:`add_json_field` — register a process-wide JSON field provider whose
  value is appended to every JSON-formatted record under the supplied
  attribute name. The provider is invoked once per ``format`` call. Values
  are emitted AFTER the stable schema fields and never overwrite them.
- :func:`remove_json_field` — unregister a provider previously installed via
  ``add_json_field``.
- :func:`clear_json_fields` — clear the registry (test isolation).
- :func:`get_registered_json_fields` — diagnostic snapshot of the registry.

The registry-style ``add_json_field`` API exists so services no longer need to
subclass or monkey-patch :class:`JSONFormatter` to inject e.g. ``severity``,
``event_type``, or ``request_id`` into every log line. Instead they register a
provider callable at startup. The provider receives the :class:`logging.LogRecord`
and returns the value (or ``None`` to skip emission for that record).
"""

from cloud_dog_logging.formatters.json_formatter import (
    JSONFormatter,
    JSONFieldProvider,
    add_json_field,
    clear_json_fields,
    get_registered_json_fields,
    remove_json_field,
)
from cloud_dog_logging.formatters.text_formatter import TextFormatter

__all__ = [
    "JSONFormatter",
    "TextFormatter",
    "JSONFieldProvider",
    "add_json_field",
    "remove_json_field",
    "clear_json_fields",
    "get_registered_json_fields",
]
