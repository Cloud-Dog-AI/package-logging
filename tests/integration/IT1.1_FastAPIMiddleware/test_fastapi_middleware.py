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

"""IT1.1: FastAPI Middleware — request logging middleware tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from cloud_dog_logging import setup_logging
from cloud_dog_logging.middleware.fastapi import LoggingMiddleware


def _create_test_app(log_file: str | None = None) -> FastAPI:
    """Create a minimal FastAPI app with logging middleware."""
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/test")
    async def test_endpoint() -> dict:
        return {"status": "ok"}

    @app.get("/error")
    async def error_endpoint() -> dict:
        raise ValueError("Test error")

    return app


@pytest.mark.asyncio
class TestFastAPIMiddleware:
    """Test suite for FastAPI logging middleware."""

    async def test_request_logged_with_method_path(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "middleware-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert response.status_code == 200
        content = Path(app_log).read_text()
        assert "GET" in content
        assert "/test" in content

    async def test_correlation_id_injected_in_response(self) -> None:
        setup_logging({"service_name": "corr-test"})
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        assert "X-Request-Id" in response.headers

    async def test_existing_request_id_preserved(self) -> None:
        setup_logging({"service_name": "preserve-test"})
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test", headers={"X-Request-Id": "custom-id-123"})

        assert response.headers.get("X-Request-Id") == "custom-id-123"

    async def test_missing_request_id_generated(self) -> None:
        setup_logging({"service_name": "gen-test"})
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/test")

        request_id = response.headers.get("X-Request-Id")
        assert request_id is not None
        assert len(request_id) > 0

    async def test_request_duration_logged(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "duration-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/test")

        content = Path(app_log).read_text()
        assert "duration_ms" in content

    async def test_status_code_logged(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "status-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        app = _create_test_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.get("/test")

        content = Path(app_log).read_text()
        assert "200" in content
