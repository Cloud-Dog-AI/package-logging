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

"""UT1.4: Correlation ID — context-local correlation ID tests."""

from __future__ import annotations

import asyncio
import re

from cloud_dog_logging.correlation import (
    clear_correlation_id,
    get_correlation_id,
    set_correlation_id,
    get_service_name,
    set_service_name,
)


class TestCorrelationID:
    """Test suite for correlation ID context management."""

    def test_generate_new_id_when_none_set(self) -> None:
        clear_correlation_id()
        cid = get_correlation_id()
        assert cid is not None
        assert len(cid) == 32  # UUID hex

    def test_set_and_get(self) -> None:
        set_correlation_id("my-custom-id")
        assert get_correlation_id() == "my-custom-id"

    def test_clear_resets(self) -> None:
        set_correlation_id("id-to-clear")
        clear_correlation_id()
        # Should generate a new one
        cid = get_correlation_id()
        assert cid != "id-to-clear"

    def test_id_is_uuid_hex_format(self) -> None:
        clear_correlation_id()
        cid = get_correlation_id()
        assert re.match(r"^[0-9a-f]{32}$", cid)

    def test_id_contains_no_sensitive_info(self) -> None:
        """CS1.3: Correlation IDs MUST NOT contain sensitive information."""
        clear_correlation_id()
        cid = get_correlation_id()
        # UUID hex — just hex characters, no PII or secrets
        assert re.match(r"^[0-9a-f]+$", cid)

    def test_service_name_set_and_get(self) -> None:
        set_service_name("my-service")
        assert get_service_name() == "my-service"

    def test_default_service_name(self) -> None:
        # After reset in conftest, default should be set
        name = get_service_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_async_propagation(self) -> None:
        """Correlation ID MUST propagate across async tasks via contextvars."""

        async def _run() -> str:
            set_correlation_id("async-test-id")

            async def inner_task() -> str:
                return get_correlation_id()

            result = await inner_task()
            return result

        result = asyncio.run(_run())
        assert result == "async-test-id"

    def test_isolation_between_contexts(self) -> None:
        """Correlation IDs MUST be isolated between different contexts."""

        async def _run() -> tuple[str, str]:
            results: list[str] = []

            async def task_a() -> None:
                set_correlation_id("task-a-id")
                await asyncio.sleep(0.01)
                results.append(get_correlation_id())

            async def task_b() -> None:
                set_correlation_id("task-b-id")
                await asyncio.sleep(0.01)
                results.append(get_correlation_id())

            # Note: contextvars copy on task creation
            t1 = asyncio.create_task(task_a())
            t2 = asyncio.create_task(task_b())
            await t1
            await t2
            return results[0], results[1]

        a_id, b_id = asyncio.run(_run())
        assert a_id == "task-a-id"
        assert b_id == "task-b-id"
