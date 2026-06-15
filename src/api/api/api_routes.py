import asyncio
import json
import logging
import math
import os
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
import requests
from azure.ai.projects.aio import AIProjectClient
from common.config.config import Config
from api.models.input_models import ChartFilters
from services.chat_service import ChatService
from services.chart_service import ChartService
from services.model_service import ModelService
from common.logging.event_utils import track_event_if_configured
from helpers.azure_credential_utils import get_azure_credential, get_azure_credential_async
from auth.auth_utils import get_authenticated_user_details
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

router = APIRouter()

logger = logging.getLogger(__name__)


async def _build_model_service():
    """Yield a ModelService backed by a fresh AIProjectClient.

    The AIProjectClient (azure.ai.projects.aio) exposes both the deployments
    listing and the agent version-management methods the ModelService needs.

    Both the credential and the client are entered as async context managers so
    aiohttp's underlying ``ClientSession`` and ``TCPConnector`` are released
    cleanly when the request completes (without this we leak them and the
    log shows "Unclosed client session / Unclosed connector" on every call).
    """
    config = Config()
    credential = await get_azure_credential_async(client_id=config.azure_client_id or None)
    async with credential:
        async with AIProjectClient(
            endpoint=config.ai_project_endpoint,
            credential=credential,
        ) as project_client:
            yield ModelService(
                project_client=project_client,
                conversation_agent_name=config.orchestrator_agent_name,
                title_agent_name=config.title_agent_name,
                chat_service=ChatService(),
                search_connection_name=config.azure_ai_search_connection_name or "",
                search_index_name=config.azure_ai_search_index or "",
            )


@router.get("/fetchChartData")
async def fetch_chart_data():
    try:
        logger.info("GET /fetchChartData called")
        chart_service = ChartService()
        response = await chart_service.fetch_chart_data()
        track_event_if_configured(
            "FetchChartDataSuccess",
            {"status": "success", "source": "/fetchChartData"}
        )
        return JSONResponse(content=response)
    except Exception as e:
        logger.exception("Error in fetch_chart_data: %s", str(e))
        track_event_if_configured("FetchChartDataError", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        span = trace.get_current_span()
        if span is not None:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
        return JSONResponse(content={"error": "Failed to fetch chart data due to an internal error."}, status_code=500)


@router.post("/fetchChartDataWithFilters")
async def fetch_chart_data_with_filters(chart_filters: ChartFilters):
    try:
        logger.info("Received filters: %s", chart_filters)
        chart_service = ChartService()
        response = await chart_service.fetch_chart_data_with_filters(chart_filters)
        track_event_if_configured(
            "FetchChartDataWithFiltersSuccess",
            {"status": "success", "filters": chart_filters.model_dump()}
        )
        # Sanitize the response to handle NaN and Infinity values
        for record in response:
            if isinstance(record.get("chart_value"), list):
                for item in record["chart_value"]:
                    if isinstance(item.get("value"), float) and (math.isnan(item["value"]) or math.isinf(item["value"])):
                        item["value"] = None
        return JSONResponse(content=response)
    except Exception as e:
        logger.exception("Error in fetch_chart_data_with_filters: %s", str(e))
        track_event_if_configured("FetchChartDataWithFiltersError", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        span = trace.get_current_span()
        if span is not None:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
        return JSONResponse(content={"error": "Failed to fetch chart data due to an internal error."}, status_code=500)


@router.get("/fetchFilterData")
async def fetch_filter_data():
    try:
        logger.info("GET /fetchFilterData called")
        chart_service = ChartService()
        response = await chart_service.fetch_filter_data()
        track_event_if_configured(
            "FetchFilterDataSuccess",
            {"status": "success", "source": "/fetchFilterData"}
        )
        return JSONResponse(content=response)
    except Exception as e:
        logger.exception("Error in fetch_filter_data: %s", str(e))
        track_event_if_configured("FetchFilterDataError", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        span = trace.get_current_span()
        if span is not None:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
        return JSONResponse(content={"error": "Failed to fetch filter data due to an internal error."}, status_code=500)


@router.post("/chat")
async def conversation(request: Request):
    try:
        # Get the request JSON and last RAG response from the client
        request_json = await request.json()
        conversation_id = request_json.get("conversation_id")
        query = request_json.get("query")
        authenticated_user = get_authenticated_user_details(request_headers=request.headers)
        user_id = authenticated_user.get("user_principal_id", "")
        logger.info("POST /chat called: conversation_id=%s, query_length=%d",
                    conversation_id, len(query) if query else 0)

        # Track chat request initiation
        track_event_if_configured("ChatRequestReceived", {
            "conversation_id": conversation_id,
            "user_id": user_id
        })

        # Attach conversation_id to current span for Application Insights correlation
        span = trace.get_current_span()
        if span and conversation_id:
            span.set_attribute("conversation_id", conversation_id)

        chat_service = ChatService()
        result = await chat_service.stream_chat_request(conversation_id, query, user_id=user_id)
        logger.info("Chat stream initiated successfully for conversation_id=%s", conversation_id)
        track_event_if_configured(
            "ChatStreamSuccess",
            {"conversation_id": conversation_id, "user_id": user_id, "query": query}
        )
        return StreamingResponse(result, media_type="application/json-lines")

    except Exception as ex:
        logger.exception("Error in conversation endpoint: %s", str(ex))

        # Track specific error type
        track_event_if_configured("ChatRequestError", {
            "conversation_id": request_json.get("conversation_id") if 'request_json' in locals() else "",
            "user_id": locals().get("user_id", ""),
            "error": str(ex),
            "error_type": type(ex).__name__
        })

        span = trace.get_current_span()
        if span is not None:
            span.record_exception(ex)
            span.set_status(Status(StatusCode.ERROR, str(ex)))
        return JSONResponse(content={"error": "An internal error occurred while processing the conversation."}, status_code=500)


@router.get("/models")
async def get_models(
    service: Annotated[ModelService, Depends(_build_model_service)],
):
    """List chat-capable model deployments available in the Foundry project."""
    logger.info("GET /models called")
    try:
        return JSONResponse(content=await service.list_models())
    except Exception as exc:
        logger.exception("Error listing models: %s", exc)
        return JSONResponse(
            content={"error": "Failed to list models due to an internal error."},
            status_code=500,
        )


@router.post("/models/select")
async def select_model(
    request: Request,
    service: Annotated[ModelService, Depends(_build_model_service)],
):
    """Apply the selected model to both chat agents (global change)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"error": "Invalid request body."}, status_code=400)

    model = body.get("model")
    model_id = model.strip() if isinstance(model, str) else model
    if not model_id:
        return JSONResponse(content={"error": "'model' is required."}, status_code=400)

    logger.info("POST /models/select called: model=%s", model_id)
    try:
        result = await service.select_model(model_id)
    except ValueError as exc:
        return JSONResponse(content={"error": str(exc)}, status_code=400)
    except Exception as exc:
        logger.exception("Error selecting model %s: %s", model_id, exc)
        span = trace.get_current_span()
        if span is not None:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
        return JSONResponse(
            content={"error": "Failed to apply model selection due to an internal error."},
            status_code=500,
        )

    return JSONResponse(content=result)


@router.get("/models/status")
async def get_model_status(
    service: Annotated[ModelService, Depends(_build_model_service)],
):
    """Return the readiness status of the chat agents' current model.

    Used by the UI to poll after a /models/select call, since Foundry takes
    1-2 minutes to provision a newly-published agent version before it can
    serve chat traffic. ``status`` is "active" when both agents' latest
    versions are bound and ready; "creating" while still provisioning;
    "failed" if Foundry reports a permanent error.
    """
    logger.info("GET /models/status called")
    try:
        return JSONResponse(content=await service.get_status())
    except Exception as exc:
        logger.exception("Error getting model status: %s", exc)
        return JSONResponse(
            content={"error": "Failed to read model status due to an internal error."},
            status_code=500,
        )


@router.get("/layout-config")
async def get_layout_config():
    logger.info("GET /layout-config called")
    layout_config_str = os.getenv("REACT_APP_LAYOUT_CONFIG", "")
    if layout_config_str:
        try:
            layout_config_json = json.loads(layout_config_str)
            track_event_if_configured("LayoutConfigFetched", {"status": "success"})  # Parse the string into JSON
            return JSONResponse(content=layout_config_json)    # Return the parsed JSON
        except json.JSONDecodeError as e:
            logger.exception("Failed to parse layout config JSON: %s", str(e))
            track_event_if_configured("LayoutConfigParseError", {
                "error": str(e),
                "error_type": "JSONDecodeError"
            })
            span = trace.get_current_span()
            if span is not None:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            return JSONResponse(content={"error": "Invalid layout configuration format."}, status_code=400)
    track_event_if_configured("LayoutConfigNotFound", {})
    return JSONResponse(content={"error": "Layout config not found in environment variables"}, status_code=400)


@router.get("/display-chart-default")
async def get_chart_config():
    logger.info("GET /display-chart-default called")
    chart_config = os.getenv("DISPLAY_CHART_DEFAULT", "")
    if chart_config:
        track_event_if_configured("ChartDisplayDefaultFetched", {"value": chart_config})
        return JSONResponse(content={"isChartDisplayDefault": chart_config})
    track_event_if_configured("ChartDisplayDefaultNotFound", {})
    return JSONResponse(content={"error": "DISPLAY_CHART_DEFAULT flag not found in environment variables"}, status_code=400)


@router.post("/fetch-azure-search-content")
async def fetch_azure_search_content_endpoint(request: Request):
    """
    API endpoint to fetch content from a given URL using the Azure AI Search API.
    Expects a JSON payload with a 'url' field.
    """
    try:
        # Parse the request JSON
        request_json = await request.json()
        url = request_json.get("url")
        logger.info("POST /fetch-azure-search-content called: url=%s", url)

        if not url:
            return JSONResponse(content={"error": "URL is required"}, status_code=400)

        # Get Azure AD token
        config = Config()
        credential = get_azure_credential(client_id=config.azure_client_id)
        token = credential.get_token("https://search.azure.com/.default")
        access_token = token.token

        # Define blocking request call
        def fetch_content():
            try:
                response = requests.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content", "")
                    title = data.get("sourceurl", "")
                    logger.info("Azure Search content fetched successfully: url=%s", url)
                    return {"content": content, "title": title}
                else:
                    logger.warning("Azure Search content fetch failed: url=%s, status=%d", url, response.status_code)
                    return {"error": f"HTTP {response.status_code}"}
            except Exception:
                logger.exception("Exception occurred while making the HTTP request")
                return {"error": "Unable to fetch content"}

        result = await asyncio.to_thread(fetch_content)

        return JSONResponse(content=result)

    except Exception:
        logger.exception("Error in fetch_azure_search_content_endpoint")
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=500
        )
