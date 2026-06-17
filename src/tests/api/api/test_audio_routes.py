"""Tests for src/api/api/audio_routes.py — audio SAS URL endpoint.

Follows the same httpx.AsyncClient pattern as test_drill_routes.py.
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.audio_routes import router

app = FastAPI()
app.include_router(router, prefix="/api/audio")


@pytest.fixture
def headers():
    return {"X-Ms-Client-Principal-Id": "user-42"}


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


CONV_ID = "03b0e193-5b55-42d3-a258-b0ff9336ae18"


@pytest.mark.asyncio
@patch("api.audio_routes.get_audio_url")
async def test_audio_available(mock_get, client, headers):
    mock_get.return_value = {
        "available": True,
        "url": "https://st.blob.core.windows.net/data/custom_audiodata/convo_03b0.wav?sig=abc",
        "filename": "convo_03b0.wav",
    }
    res = await client.get(f"/api/audio/{CONV_ID}", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["available"] is True
    assert "url" in body
    mock_get.assert_called_once_with(CONV_ID)


@pytest.mark.asyncio
@patch("api.audio_routes.get_audio_url")
async def test_audio_not_found(mock_get, client, headers):
    mock_get.return_value = None
    res = await client.get(f"/api/audio/{CONV_ID}", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["available"] is False


@pytest.mark.asyncio
@patch("api.audio_routes.get_audio_url")
async def test_audio_service_error(mock_get, client, headers):
    mock_get.side_effect = RuntimeError("storage down")
    res = await client.get(f"/api/audio/{CONV_ID}", headers=headers)
    assert res.status_code == 500
    body = res.json()
    assert body["available"] is False
