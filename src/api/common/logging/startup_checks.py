"""Startup dependency probes for the API.

These probes run once at application startup (inside the FastAPI lifespan handler)
and again on demand from the ``/health/ready`` endpoint. Each probe is fully
defensive: any failure is caught, logged with full context (no secrets), and
reported as ``ok=False`` in the result dict so the app can still start and serve
the health endpoints even when a dependency is down.

The intent is that when something goes wrong in production, the App Service
``Log stream`` shows immediately *which* dependency failed, *why*, and *how long*
the probe took, instead of a silent hang.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import time
from dataclasses import dataclass, asdict
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

logger = logging.getLogger("startup_checks")


@dataclass
class ProbeResult:
    name: str
    ok: bool
    duration_ms: int
    detail: str
    skipped: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _redact_endpoint(value: str | None) -> str:
    """Return the host portion of a URL, never the full URL with query/keys."""
    if not value:
        return "<unset>"
    try:
        parsed = urlparse(value)
        if parsed.hostname:
            port = f":{parsed.port}" if parsed.port else ""
            return f"{parsed.scheme}://{parsed.hostname}{port}"
        return value
    except Exception:
        return "<unparseable>"


async def _run_probe(name: str, fn: Callable[[], Awaitable[str]]) -> ProbeResult:
    """Run a single probe, capturing timing and exceptions."""
    started = time.perf_counter()
    try:
        detail = await fn()
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.info("Dependency probe OK  | %-18s | %4d ms | %s", name, duration_ms, detail)
        return ProbeResult(name=name, ok=True, duration_ms=duration_ms, detail=detail)
    except _SkippedProbe as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.warning(
            "Dependency probe SKIP | %-18s | %4d ms | %s", name, duration_ms, exc
        )
        return ProbeResult(
            name=name, ok=True, duration_ms=duration_ms, detail=str(exc), skipped=True
        )
    except Exception as exc:  # noqa: BLE001 — we want to catch everything here
        duration_ms = int((time.perf_counter() - started) * 1000)
        logger.exception(
            "Dependency probe FAIL | %-18s | %4d ms | %s: %s",
            name,
            duration_ms,
            type(exc).__name__,
            exc,
        )
        return ProbeResult(
            name=name,
            ok=False,
            duration_ms=duration_ms,
            detail=f"{type(exc).__name__}: {exc}",
        )


class _SkippedProbe(Exception):
    """Raised by a probe when the dependency isn't configured (not a failure)."""


# ---------------------------------------------------------------------------
# Individual probes
# ---------------------------------------------------------------------------

async def _probe_app_insights() -> str:
    conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn:
        raise _SkippedProbe("APPLICATIONINSIGHTS_CONNECTION_STRING not set")
    # Don't log the full connection string — it embeds the instrumentation key.
    return f"connection string set ({len(conn)} chars)"


async def _probe_dns(host: str) -> str:
    loop = asyncio.get_running_loop()
    addrs = await loop.run_in_executor(None, socket.gethostbyname_ex, host)
    return f"resolved {host} -> {addrs[2]}"


async def _probe_sql() -> str:
    server = os.getenv("SQLDB_SERVER")
    database = os.getenv("SQLDB_DATABASE")
    if not server or not database:
        raise _SkippedProbe("SQLDB_SERVER / SQLDB_DATABASE not set")

    # DNS first — distinguishes "DNS / firewall" from "auth" failures.
    await _probe_dns(server)

    # Actual connection attempt via the existing helper. Imports are deferred
    # so a missing ODBC driver shows up as a clean probe failure rather than
    # blowing up app import.
    from common.database.sqldb_service import get_db_connection  # noqa: WPS433

    conn = await get_db_connection()
    try:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        finally:
            cursor.close()
    finally:
        conn.close()
    return f"connected to {server}/{database}"


async def _probe_cosmos() -> str:
    enabled = os.getenv("USE_CHAT_HISTORY_ENABLED", "false").strip().lower() == "true"
    if not enabled:
        raise _SkippedProbe("USE_CHAT_HISTORY_ENABLED is false")

    account = os.getenv("AZURE_COSMOSDB_ACCOUNT")
    database = os.getenv("AZURE_COSMOSDB_DATABASE")
    container = os.getenv("AZURE_COSMOSDB_CONVERSATIONS_CONTAINER")
    if not (account and database and container):
        raise _SkippedProbe("Cosmos account/database/container env vars not set")

    endpoint = f"https://{account}.documents.azure.com:443/"
    await _probe_dns(f"{account}.documents.azure.com")

    from helpers.azure_credential_utils import get_azure_credential_async  # noqa: WPS433
    from common.database.cosmosdb_service import CosmosConversationClient  # noqa: WPS433

    client_id = os.getenv("AZURE_CLIENT_ID") or None
    credential = await get_azure_credential_async(client_id=client_id)
    try:
        client = CosmosConversationClient(
            cosmosdb_endpoint=endpoint,
            credential=credential,
            database_name=database,
            container_name=container,
        )
        ok, msg = await client.ensure()
        if not ok:
            raise RuntimeError(msg)
    finally:
        if hasattr(credential, "close"):
            await credential.close()
    return f"connected to {endpoint} db={database} container={container}"


async def _probe_ai_search() -> str:
    endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
    index = os.getenv("AZURE_AI_SEARCH_INDEX")
    if not endpoint:
        raise _SkippedProbe("AZURE_AI_SEARCH_ENDPOINT not set")

    parsed = urlparse(endpoint)
    if parsed.hostname:
        await _probe_dns(parsed.hostname)
    return f"endpoint reachable {_redact_endpoint(endpoint)} (index={index or '<unset>'})"


async def _probe_ai_foundry() -> str:
    endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
    if not endpoint:
        raise _SkippedProbe("AZURE_AI_AGENT_ENDPOINT not set")

    parsed = urlparse(endpoint)
    if parsed.hostname:
        await _probe_dns(parsed.hostname)
    return f"endpoint reachable {_redact_endpoint(endpoint)}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

ALL_PROBES: list[tuple[str, Callable[[], Awaitable[str]]]] = [
    ("app_insights", _probe_app_insights),
    ("sql_database", _probe_sql),
    ("cosmos_db", _probe_cosmos),
    ("ai_search", _probe_ai_search),
    ("ai_foundry", _probe_ai_foundry),
]


async def run_all_probes() -> list[ProbeResult]:
    """Run every dependency probe sequentially and return their results."""
    results: list[ProbeResult] = []
    for name, fn in ALL_PROBES:
        results.append(await _run_probe(name, fn))
    return results


def log_startup_banner(app_version: str) -> None:
    """Log a one-shot startup banner with the most useful diagnostic context."""
    logger.info("=" * 72)
    logger.info("Conversation Knowledge Mining API starting up")
    logger.info("  app_version           : %s", app_version)
    logger.info("  app_env               : %s", os.getenv("APP_ENV", "<unset>"))
    logger.info("  solution_name         : %s", os.getenv("SOLUTION_NAME", "<unset>"))
    logger.info("  resource_group        : %s", os.getenv("RESOURCE_GROUP_NAME", "<unset>"))
    logger.info("  hostname              : %s", socket.gethostname())
    logger.info("  python_version        : %s", os.getenv("PYTHON_VERSION", "<unknown>"))
    logger.info("  azure_client_id_set   : %s", bool(os.getenv("AZURE_CLIENT_ID")))
    logger.info("  app_insights_set      : %s", bool(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")))
    logger.info("  sqldb_server          : %s", os.getenv("SQLDB_SERVER", "<unset>"))
    logger.info("  sqldb_database        : %s", os.getenv("SQLDB_DATABASE", "<unset>"))
    logger.info("  cosmosdb_account      : %s", os.getenv("AZURE_COSMOSDB_ACCOUNT", "<unset>"))
    logger.info("  ai_search_endpoint    : %s", _redact_endpoint(os.getenv("AZURE_AI_SEARCH_ENDPOINT")))
    logger.info("  ai_search_index       : %s", os.getenv("AZURE_AI_SEARCH_INDEX", "<unset>"))
    logger.info("  ai_foundry_endpoint   : %s", _redact_endpoint(os.getenv("AZURE_AI_AGENT_ENDPOINT")))
    logger.info("  ai_foundry_model      : %s", os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME", "<unset>"))
    logger.info("  use_chat_history      : %s", os.getenv("USE_CHAT_HISTORY_ENABLED", "<unset>"))
    logger.info("=" * 72)
