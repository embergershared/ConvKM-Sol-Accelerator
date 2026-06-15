"""Dashboard drill-down routes — see plans/dashboard-drill-down.md (Stage B).

Mount path: /api/drill (set in app.py).

Auth pattern: capture-only. Mirrors history_routes.py — every handler calls
`get_authenticated_user_details(request.headers)` so the resolved principal (or
the local-dev fallback from auth/sample_user.py) is attached to every telemetry
event under `user_id`. None of these endpoints refuse a request when the
EasyAuth headers are absent. A stricter gate can be added later as a single
router-level `Depends(...)` without touching call sites. See Resolved
decisions §1 in plans/dashboard-drill-down.md.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from api.models.input_models import DrillCallsRequest, DrillTimeseriesRequest
from auth.auth_utils import get_authenticated_user_details
from common.logging.event_utils import track_event_if_configured
from services.drill_service import DrillService

router = APIRouter()
logger = logging.getLogger(__name__)
drill_service = DrillService()


def _resolve_user_id(request: Request) -> str:
    """Capture-only — returns the EasyAuth principal id, or 'local-dev'."""
    try:
        details = get_authenticated_user_details(request_headers=request.headers)
        return details.get("user_principal_id") or "local-dev"
    except Exception:  # pragma: no cover — header parsing should never raise
        return "local-dev"


@router.post("/timeseries")
async def drill_timeseries(payload: DrillTimeseriesRequest, request: Request):
    user_id = _resolve_user_id(request)
    try:
        logger.info(
            "POST /api/drill/timeseries dim=%s value=%s bucket=%s user=%s",
            payload.selection.dimension,
            payload.selection.value,
            payload.bucket,
            user_id,
        )
        result = await drill_service.fetch_timeseries(payload)
        track_event_if_configured(
            "DrillTimeseriesSuccess",
            {
                "user_id": user_id,
                "dimension": payload.selection.dimension,
                "bucket": payload.bucket,
                "rows": len(result),
            },
        )
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /api/drill/timeseries: %s", e)
        track_event_if_configured(
            "DrillTimeseriesError",
            {
                "user_id": user_id,
                "dimension": payload.selection.dimension,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        span = trace.get_current_span()
        if span is not None:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
        return JSONResponse(
            content={"error": "Failed to fetch drill timeseries due to an internal error."},
            status_code=500,
        )


@router.post("/calls")
async def drill_calls(payload: DrillCallsRequest, request: Request):
    user_id = _resolve_user_id(request)
    try:
        logger.info(
            "POST /api/drill/calls dim=%s value=%s offset=%d limit=%d user=%s",
            payload.selection.dimension,
            payload.selection.value,
            payload.offset,
            payload.limit,
            user_id,
        )
        result = await drill_service.fetch_calls(payload)
        track_event_if_configured(
            "DrillCallsSuccess",
            {
                "user_id": user_id,
                "dimension": payload.selection.dimension,
                "offset": payload.offset,
                "limit": payload.limit,
                "total": result.get("total", 0),
                "returned": len(result.get("items", [])),
            },
        )
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /api/drill/calls: %s", e)
        track_event_if_configured(
            "DrillCallsError",
            {
                "user_id": user_id,
                "dimension": payload.selection.dimension,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        span = trace.get_current_span()
        if span is not None:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
        return JSONResponse(
            content={"error": "Failed to fetch drill calls due to an internal error."},
            status_code=500,
        )


@router.get("/call/{conversation_id}")
async def drill_call_detail(conversation_id: str, request: Request):
    user_id = _resolve_user_id(request)
    try:
        logger.info(
            "GET /api/drill/call/%s user=%s", conversation_id, user_id
        )
        span = trace.get_current_span()
        if span is not None:
            span.set_attribute("conversation_id", conversation_id)
        result = await drill_service.fetch_call(conversation_id)
        track_event_if_configured(
            "DrillCallDetailSuccess",
            {"user_id": user_id, "conversation_id": conversation_id},
        )
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /api/drill/call/{id}: %s", e)
        track_event_if_configured(
            "DrillCallDetailError",
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        span = trace.get_current_span()
        if span is not None:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
        return JSONResponse(
            content={"error": "Failed to fetch call detail due to an internal error."},
            status_code=500,
        )
