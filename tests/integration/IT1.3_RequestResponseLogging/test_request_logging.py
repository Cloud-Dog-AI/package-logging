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

"""IT1.3: Request/Response Logging — full request/response logging cycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from cloud_dog_logging import setup_logging
from cloud_dog_logging.middleware.fastapi import LoggingMiddleware


def _create_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/success")
    async def success() -> dict:
        return {"result": "ok"}

    @app.get("/fail")
    async def fail() -> dict:
        raise ValueError("Deliberate failure")

    return app


@pytest.mark.asyncio
class TestRequestResponseLogging:
    """Test suite for full request/response logging cycle."""

    async def test_success_request_logged(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "req-log-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        app = _create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/success")

        content = Path(app_log).read_text()
        assert "Request started" in content
        assert "Request completed" in content
        assert "200" in content

    async def test_error_request_logged(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "err-log-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        app = _create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            try:
                await client.get("/fail")
            except Exception:
                pass

        content = Path(app_log).read_text()
        assert "Request started" in content

    async def test_duration_ms_present(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "dur-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        app = _create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/success")

        content = Path(app_log).read_text()
        # Find the "Request completed" line and verify duration_ms
        for line in content.strip().splitlines():
            parsed = json.loads(line)
            if parsed.get("message") == "Request completed":
                assert "duration_ms" in parsed.get("extra", {})
                assert isinstance(parsed["extra"]["duration_ms"], (int, float))

    async def test_no_secrets_in_logged_headers(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "header-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        app = _create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get(
                "/success",
                headers={
                    "Authorization": "Bearer super-secret-token",
                    "X-API-Key": "my-api-key-value",
                },
            )

        content = Path(app_log).read_text()
        # The middleware should not log raw header values for sensitive headers
        assert "super-secret-token" not in content
        assert "my-api-key-value" not in content
