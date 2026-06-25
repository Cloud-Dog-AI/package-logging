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

"""IT1.2: Correlation Propagation — correlation ID flow through requests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from cloud_dog_logging import setup_logging, get_logger
from cloud_dog_logging.middleware.fastapi import LoggingMiddleware
from cloud_dog_logging.correlation import get_correlation_id


def _create_corr_app() -> FastAPI:
    """Create a test app that returns the correlation ID."""
    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/corr")
    async def corr_endpoint() -> dict:
        cid = get_correlation_id()
        logger = get_logger("test.corr")
        logger.info("Inside handler", correlation_id=cid)
        return {"correlation_id": cid}

    return app


@pytest.mark.asyncio
class TestCorrelationPropagation:
    """Test suite for correlation ID propagation through requests."""

    async def test_incoming_request_id_used(self) -> None:
        setup_logging({"service_name": "corr-prop-test"})
        app = _create_corr_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/corr", headers={"X-Request-Id": "incoming-id-999"})
        data = response.json()
        assert data["correlation_id"] == "incoming-id-999"

    async def test_missing_header_generates_id(self) -> None:
        setup_logging({"service_name": "corr-gen-test"})
        app = _create_corr_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/corr")
        data = response.json()
        assert data["correlation_id"] is not None
        assert len(data["correlation_id"]) > 0

    async def test_all_log_entries_share_same_id(self, tmp_path: Path) -> None:
        app_log = str(tmp_path / "app.log")
        setup_logging(
            {
                "service_name": "corr-share-test",
                "log": {"level": "DEBUG", "app_log": app_log, "console": False},
            }
        )
        app = _create_corr_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/corr", headers={"X-Request-Id": "shared-corr-id"})
        assert response.status_code == 200

        content = Path(app_log).read_text()
        lines = [line for line in content.strip().splitlines() if line.strip()]
        # All log lines from our middleware/handler should share the same ID
        matched = 0
        for line in lines:
            parsed = json.loads(line)
            # Only check lines from our middleware or the test handler
            logger_name = parsed.get("logger", "")
            if logger_name.startswith(("cloud_dog_logging", "test.")) and logger_name != "cloud_dog_logging.integrity":
                assert parsed["correlation_id"] == "shared-corr-id", (
                    f"Logger '{logger_name}' has wrong correlation_id: {parsed['correlation_id']}"
                )
                matched += 1
        assert matched > 0, "No log lines from our middleware found"

    async def test_response_header_matches(self) -> None:
        setup_logging({"service_name": "corr-resp-test"})
        app = _create_corr_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/corr", headers={"X-Request-Id": "resp-match-id"})
        assert response.headers.get("X-Request-Id") == "resp-match-id"
        data = response.json()
        assert data["correlation_id"] == "resp-match-id"
