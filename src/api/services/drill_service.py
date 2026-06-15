"""Drill-down service — see plans/dashboard-drill-down.md (Stage B).

Mirrors the error-handling shape of `services/chart_service.py`: catch any
exception raised below the service boundary, log with stack trace, and re-raise
as an HTTPException so the FastAPI handler can return a clean 500.
"""

import logging
from typing import Optional

from fastapi import HTTPException, status

from api.models.input_models import DrillCallsRequest, DrillTimeseriesRequest
from common.database.sqldb_service import (
    fetch_call_detail,
    fetch_drill_calls,
    fetch_drill_timeseries,
)

logger = logging.getLogger(__name__)


class DrillService:
    """Service class wrapping the three drill-down SQL fetch functions."""

    async def fetch_timeseries(self, request: DrillTimeseriesRequest) -> list[dict]:
        try:
            return await fetch_drill_timeseries(
                selection=request.selection,
                bucket=request.bucket,
                global_filters=request.filters,
            )
        except ValueError as e:
            logger.warning("Bad drill timeseries request: %s", e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error("Error in DrillService.fetch_timeseries: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while fetching drill timeseries.",
            )

    async def fetch_calls(self, request: DrillCallsRequest) -> dict:
        try:
            return await fetch_drill_calls(
                selection=request.selection,
                global_filters=request.filters,
                time_range=request.time_range,
                offset=request.offset,
                limit=request.limit,
            )
        except ValueError as e:
            logger.warning("Bad drill calls request: %s", e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error("Error in DrillService.fetch_calls: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while fetching drill calls.",
            )

    async def fetch_call(self, conversation_id: str) -> Optional[dict]:
        try:
            detail = await fetch_call_detail(conversation_id)
            if detail is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found.",
                )
            return detail
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error in DrillService.fetch_call: %s", e, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while fetching the call detail.",
            )
