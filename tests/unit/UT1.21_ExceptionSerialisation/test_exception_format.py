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

"""UT1.21: format_exception utility tests."""

from __future__ import annotations

from cloud_dog_logging.exceptions import format_exception


def _raise_value_error() -> None:
    raise ValueError("bad value")


def _raise_runtime_error() -> None:
    raise RuntimeError("runtime issue")


class TestExceptionSerialisation:
    def test_format_exception_fields(self) -> None:
        try:
            _raise_value_error()
        except ValueError as exc:
            payload = format_exception(exc)

        assert payload["type"] == "ValueError"
        assert payload["message"] == "bad value"
        assert isinstance(payload["stack_hash"], str)
        assert len(payload["stack_hash"]) == 64
        assert isinstance(payload["traceback"], list)
        assert payload["traceback"]

    def test_same_exception_shape_produces_same_hash(self) -> None:
        try:
            _raise_value_error()
        except ValueError as exc:
            h1 = format_exception(exc)["stack_hash"]

        try:
            _raise_value_error()
        except ValueError as exc:
            h2 = format_exception(exc)["stack_hash"]

        assert h1 == h2

    def test_different_exception_produces_different_hash(self) -> None:
        try:
            _raise_value_error()
        except ValueError as exc:
            h1 = format_exception(exc)["stack_hash"]

        try:
            _raise_runtime_error()
        except RuntimeError as exc:
            h2 = format_exception(exc)["stack_hash"]

        assert h1 != h2

    def test_nested_exception_serialises(self) -> None:
        try:
            try:
                _raise_value_error()
            except ValueError as inner:
                raise RuntimeError("wrapped") from inner
        except RuntimeError as exc:
            payload = format_exception(exc)

        assert payload["type"] == "RuntimeError"
        joined = "\n".join(payload["traceback"])  # type: ignore[arg-type]
        assert "ValueError" in joined
