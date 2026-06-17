"""Audio routes — serve SAS URLs for call recording playback.

Mount path: /api/audio (set in app.py).
"""

import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from auth.auth_utils import get_authenticated_user_details
from common.logging.event_utils import track_event_if_configured
from services.audio_service import get_audio_url

router = APIRouter()
logger = logging.getLogger(__name__)


def _resolve_user_id(request: Request) -> str:
    try:
        details = get_authenticated_user_details(request_headers=request.headers)
        return details.get("user_principal_id") or "local-dev"
    except Exception:
        return "local-dev"


@router.get("/{conversation_id}")
async def get_audio(conversation_id: str, request: Request):
    """Return a short-lived SAS URL for the call recording, if available."""
    user_id = _resolve_user_id(request)
    try:
        logger.info(
            "GET /api/audio/%s user=%s", conversation_id, user_id
        )
        result = await asyncio.to_thread(get_audio_url, conversation_id)
        if result is None:
            track_event_if_configured(
                "AudioNotFound",
                {"user_id": user_id, "conversation_id": conversation_id},
            )
            return JSONResponse(content={"available": False})

        track_event_if_configured(
            "AudioUrlGenerated",
            {"user_id": user_id, "conversation_id": conversation_id},
        )
        return JSONResponse(content=result)

    except Exception as e:
        logger.exception("Error in /api/audio/%s: %s", conversation_id, e)
        track_event_if_configured(
            "AudioError",
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "error": str(e),
            },
        )
        return JSONResponse(
            content={"available": False, "error": "Failed to check audio availability."},
            status_code=500,
        )
