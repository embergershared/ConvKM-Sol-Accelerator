"""Tests for src/api/api/drill_routes.py — the 3 Stage B drill endpoints.

Mirrors the pattern in tests/api/api/test_history_routes.py:
build a FastAPI app around the router, patch the auth + service layer, hit it
with httpx.AsyncClient and assert status/body.
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, status
from httpx import ASGITransport, AsyncClient

from api.drill_routes import router


app = FastAPI()
app.include_router(router, prefix="/api/drill")


@pytest.fixture
def headers():
    return {"X-Ms-Client-Principal-Id": "user-42"}


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# /api/drill/timeseries
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("api.drill_routes.DrillService.fetch_timeseries", new_callable=AsyncMock)
async def test_timeseries_success(mock_fetch, client, headers):
    mock_fetch.return_value = [
        {
            "bucket_start": "2024-12-02T00:00:00",
            "calls": 4,
            "avg_sentiment_score": 0.5,
            "satisfied_pct": 75.0,
            "avg_handle_time_min": 9.5,
        }
    ]
    res = await client.post(
        "/api/drill/timeseries",
        json={
            "selection": {"dimension": "topic", "value": "Billing"},
            "bucket": "week",
        },
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert body[0]["calls"] == 4
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_timeseries_validation_error(client, headers):
    res = await client.post(
        "/api/drill/timeseries",
        json={"selection": {"dimension": "nope", "value": "x"}, "bucket": "week"},
        headers=headers,
    )
    assert res.status_code == 422  # FastAPI/Pydantic validation


@pytest.mark.asyncio
@patch("api.drill_routes.DrillService.fetch_timeseries", new_callable=AsyncMock)
async def test_timeseries_service_500(mock_fetch, client, headers):
    mock_fetch.side_effect = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="boom"
    )
    res = await client.post(
        "/api/drill/timeseries",
        json={"selection": {"dimension": "topic", "value": "Billing"}, "bucket": "week"},
        headers=headers,
    )
    assert res.status_code == 500


# ---------------------------------------------------------------------------
# /api/drill/calls
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("api.drill_routes.DrillService.fetch_calls", new_callable=AsyncMock)
async def test_calls_success(mock_fetch, client, headers):
    mock_fetch.return_value = {
        "total": 42,
        "items": [
            {
                "conversation_id": "abc-1",
                "start_time": "2024-12-02T00:01:00",
                "duration_min": 12,
                "sentiment": "Positive",
                "satisfied": "Yes",
                "topic": "Billing",
                "complaint": None,
                "summary_excerpt": "Customer asked about ...",
            }
        ],
    }
    res = await client.post(
        "/api/drill/calls",
        json={
            "selection": {"dimension": "topic", "value": "Billing"},
            "offset": 0,
            "limit": 25,
        },
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 42
    assert body["items"][0]["conversation_id"] == "abc-1"


@pytest.mark.asyncio
async def test_calls_pagination_bounds(client, headers):
    # offset must be >= 0; limit must be in [1, 100].
    res = await client.post(
        "/api/drill/calls",
        json={
            "selection": {"dimension": "topic", "value": "Billing"},
            "offset": -1,
            "limit": 25,
        },
        headers=headers,
    )
    assert res.status_code == 422
    res = await client.post(
        "/api/drill/calls",
        json={
            "selection": {"dimension": "topic", "value": "Billing"},
            "offset": 0,
            "limit": 9999,
        },
        headers=headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
@patch("api.drill_routes.DrillService.fetch_calls", new_callable=AsyncMock)
async def test_calls_with_time_range_alias(mock_fetch, client, headers):
    mock_fetch.return_value = {"total": 0, "items": []}
    res = await client.post(
        "/api/drill/calls",
        json={
            "selection": {"dimension": "topic", "value": "Billing"},
            "time_range": {
                "from": "2024-12-01T00:00:00",
                "to": "2024-12-08T00:00:00",
            },
            "offset": 0,
            "limit": 10,
        },
        headers=headers,
    )
    assert res.status_code == 200
    sent = mock_fetch.await_args.kwargs.get("request") or mock_fetch.await_args.args[0]
    assert sent.time_range is not None
    assert sent.time_range.from_ == "2024-12-01T00:00:00"
    assert sent.time_range.to == "2024-12-08T00:00:00"


# ---------------------------------------------------------------------------
# /api/drill/call/{conversation_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("api.drill_routes.DrillService.fetch_call", new_callable=AsyncMock)
async def test_call_detail_success(mock_fetch, client, headers):
    mock_fetch.return_value = {
        "conversation_id": "abc-1",
        "start_time": "2024-12-02T00:01:00",
        "end_time": "2024-12-02T00:10:00",
        "duration_min": 9,
        "sentiment": "Positive",
        "satisfied": "Yes",
        "topic": "Billing",
        "complaint": None,
        "summary": "Customer asked about billing.",
        "transcript_raw": "Hello, my name is ...",
        "key_phrases": ["billing", "address"],
    }
    res = await client.get("/api/drill/call/abc-1", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["conversation_id"] == "abc-1"
    assert body["key_phrases"] == ["billing", "address"]


@pytest.mark.asyncio
@patch("api.drill_routes.DrillService.fetch_call", new_callable=AsyncMock)
async def test_call_detail_not_found(mock_fetch, client, headers):
    mock_fetch.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="missing"
    )
    res = await client.get("/api/drill/call/does-not-exist", headers=headers)
    assert res.status_code == 404


@pytest.mark.asyncio
@patch("api.drill_routes.DrillService.fetch_call", new_callable=AsyncMock)
async def test_call_detail_no_auth_headers_local_dev(mock_fetch, client):
    """Capture-only auth: no EasyAuth headers should NOT block the request."""
    mock_fetch.return_value = {
        "conversation_id": "abc-1",
        "start_time": "2024-12-02T00:01:00",
        "end_time": "2024-12-02T00:10:00",
        "duration_min": 9,
        "sentiment": "Positive",
        "satisfied": "Yes",
        "topic": "Billing",
        "complaint": None,
        "summary": "x",
        "transcript_raw": "y",
        "key_phrases": [],
    }
    res = await client.get("/api/drill/call/abc-1")
    assert res.status_code == 200
