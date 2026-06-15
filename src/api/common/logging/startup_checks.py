"""Startup dependency probes for the API.

These probes run once at application startup (inside the FastAPI lifespan
handler, in the BACKGROUND so they never block port binding) and again on
demand from the ``/health/ready`` endpoint.

Design goals:

* **The app must always start, even when every backend is down.** A probe
  failure must never raise an unhandled exception into the lifespan.
* **A failed probe must say exactly *which layer* broke** — DNS, TCP, TLS,
  authentication, authorisation, or the SDK call itself — so a user
  reading the Azure App Service Log stream can act without re-running
  anything.
* **No secrets are logged.** URLs are reduced to ``scheme://host``,
  credentials are never serialised, and exception messages are emitted
  verbatim (Azure SDK error messages are safe — they contain status codes,
  request IDs, and human-readable detail).

Each probe runs as a small state machine that records every phase it
completes. The final ``ProbeResult.detail`` is built from those phases so
even a partial success is informative (e.g. "DNS ok, TCP ok, HTTPS ok,
auth FAILED: 403 Forbidden …").
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import ssl
import time
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse

logger = logging.getLogger("startup_checks")

# Per-phase timeout (seconds). Probes must never hang forever — a slow
# dependency that exceeds the timeout is recorded as a failure for that phase
# and the probe moves on.
_PHASE_TIMEOUT_SECONDS = 10.0


# ---------------------------------------------------------------------------
# Result objects
# ---------------------------------------------------------------------------

@dataclass
class ProbePhase:
    """One step inside a probe (DNS, TCP, TLS, auth, query, …)."""
    name: str
    ok: bool
    duration_ms: int
    detail: str = ""


@dataclass
class ProbeResult:
    name: str
    ok: bool
    duration_ms: int
    detail: str
    skipped: bool = False
    phases: list[ProbePhase] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _SkippedProbe(Exception):
    """Raised by a probe when the dependency isn't configured (not a failure)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redact_endpoint(value: str | None) -> str:
    """Return ``scheme://host[:port]`` — never the full URL with query/keys."""
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


def _exc_repr(exc: BaseException) -> str:
    """Compact, log-friendly representation of an exception (no secrets)."""
    # First line of traceback often points at the actual failing call inside
    # the SDK, which is the most useful diagnostic.
    tb_summary = traceback.format_exception_only(type(exc), exc)
    summary = "".join(tb_summary).strip().replace("\n", " | ")
    return summary or f"{type(exc).__name__}: {exc}"


def _format_phases(phases: list[ProbePhase]) -> str:
    parts: list[str] = []
    for phase in phases:
        marker = "ok" if phase.ok else "FAILED"
        detail = f" {phase.detail}" if phase.detail else ""
        parts.append(f"{phase.name}={marker} ({phase.duration_ms}ms){detail}")
    return " | ".join(parts)


class _PhaseRunner:
    """Helper that records phases and never raises into the probe body."""

    def __init__(self, probe_name: str):
        self._probe_name = probe_name
        self.phases: list[ProbePhase] = []
        self.failed: ProbePhase | None = None

    async def run(self, name: str, coro_fn: Callable[[], Awaitable[str]]) -> str | None:
        """Execute one phase under a timeout. Returns the detail string on
        success, or None if the phase failed or was skipped because a
        previous phase failed. Logs each phase as it completes.
        """
        if self.failed is not None:
            return None
        started = time.perf_counter()
        try:
            detail = await asyncio.wait_for(coro_fn(), timeout=_PHASE_TIMEOUT_SECONDS)
            duration_ms = int((time.perf_counter() - started) * 1000)
            phase = ProbePhase(name=name, ok=True, duration_ms=duration_ms, detail=detail or "")
            self.phases.append(phase)
            logger.info(
                "  %s/%s OK     | %4d ms | %s",
                self._probe_name, name, duration_ms, detail or "(no detail)",
            )
            return detail
        except asyncio.TimeoutError:
            duration_ms = int((time.perf_counter() - started) * 1000)
            phase = ProbePhase(
                name=name, ok=False, duration_ms=duration_ms,
                detail=f"phase timed out after {_PHASE_TIMEOUT_SECONDS:.0f}s",
            )
            self.phases.append(phase)
            self.failed = phase
            logger.error(
                "  %s/%s FAILED | %4d ms | TIMEOUT after %.0fs",
                self._probe_name, name, duration_ms, _PHASE_TIMEOUT_SECONDS,
            )
            return None
        except _SkippedProbe:
            raise
        except Exception as exc:  # noqa: BLE001 — we deliberately catch all
            duration_ms = int((time.perf_counter() - started) * 1000)
            phase = ProbePhase(
                name=name, ok=False, duration_ms=duration_ms,
                detail=_exc_repr(exc),
            )
            self.phases.append(phase)
            self.failed = phase
            logger.error(
                "  %s/%s FAILED | %4d ms | %s\n%s",
                self._probe_name, name, duration_ms,
                _exc_repr(exc),
                traceback.format_exc(),
            )
            return None


async def _run_probe(name: str, fn: Callable[[_PhaseRunner], Awaitable[None]]) -> ProbeResult:
    """Run one probe end-to-end. Never raises."""
    started = time.perf_counter()
    logger.info("Probe %s starting", name)
    runner = _PhaseRunner(name)
    skipped = False
    skip_reason = ""
    try:
        await fn(runner)
    except _SkippedProbe as exc:
        skipped = True
        skip_reason = str(exc)
    except Exception as exc:  # noqa: BLE001 — probe code bug, log and continue
        logger.exception(
            "Probe %s raised UNEXPECTEDLY outside its phase wrappers: %s",
            name, _exc_repr(exc),
        )
        runner.failed = ProbePhase(
            name="probe_body", ok=False, duration_ms=0,
            detail=f"unexpected probe-internal error: {_exc_repr(exc)}",
        )

    duration_ms = int((time.perf_counter() - started) * 1000)

    if skipped:
        detail = skip_reason
        logger.warning("Probe %s SKIPPED       | %4d ms | %s", name, duration_ms, detail)
        return ProbeResult(name=name, ok=True, duration_ms=duration_ms, detail=detail, skipped=True)

    ok = runner.failed is None and any(p.ok for p in runner.phases)
    detail = _format_phases(runner.phases) or "no phases were run"

    if ok:
        logger.info("Probe %s OK            | %4d ms | %s", name, duration_ms, detail)
    else:
        logger.error("Probe %s FAILED        | %4d ms | %s", name, duration_ms, detail)

    return ProbeResult(
        name=name, ok=ok, duration_ms=duration_ms,
        detail=detail, skipped=False, phases=runner.phases,
    )


# ---------------------------------------------------------------------------
# Low-level reachability primitives (DNS, TCP, TLS)
# ---------------------------------------------------------------------------

async def _phase_dns(host: str) -> str:
    loop = asyncio.get_running_loop()
    addrs = await loop.run_in_executor(None, socket.gethostbyname_ex, host)
    ips = addrs[2]
    return f"resolved {host} -> {', '.join(ips) if ips else '(no A records)'}"


async def _phase_tcp(host: str, port: int = 443) -> str:
    loop = asyncio.get_running_loop()

    def _connect():
        with socket.create_connection((host, port), timeout=_PHASE_TIMEOUT_SECONDS) as sock:
            return sock.getpeername()

    peer = await loop.run_in_executor(None, _connect)
    return f"tcp connect to {host}:{port} -> {peer[0]}:{peer[1]}"


async def _phase_tls(host: str, port: int = 443) -> str:
    loop = asyncio.get_running_loop()

    def _handshake():
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=_PHASE_TIMEOUT_SECONDS) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as tls:
                cert = tls.getpeercert()
                subject = dict(x[0] for x in cert.get("subject", []))
                issuer = dict(x[0] for x in cert.get("issuer", []))
                not_after = cert.get("notAfter", "?")
                return (
                    f"tls ok, cn={subject.get('commonName', '?')}, "
                    f"issuer={issuer.get('commonName', '?')}, expires={not_after}"
                )

    return await loop.run_in_executor(None, _handshake)


# ---------------------------------------------------------------------------
# Per-dependency probes
# ---------------------------------------------------------------------------

async def _probe_app_insights(runner: _PhaseRunner) -> None:
    conn = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not conn:
        raise _SkippedProbe("APPLICATIONINSIGHTS_CONNECTION_STRING not set")

    async def check_config() -> str:
        if "InstrumentationKey=" not in conn:
            raise RuntimeError("connection string missing 'InstrumentationKey='")
        if "IngestionEndpoint=" not in conn:
            raise RuntimeError("connection string missing 'IngestionEndpoint='")
        return f"connection string set ({len(conn)} chars)"

    await runner.run("config", check_config)


async def _probe_sql(runner: _PhaseRunner) -> None:
    server = os.getenv("SQLDB_SERVER")
    database = os.getenv("SQLDB_DATABASE")
    if not server or not database:
        raise _SkippedProbe("SQLDB_SERVER / SQLDB_DATABASE not set")

    await runner.run("dns", lambda: _phase_dns(server))
    await runner.run("tcp_1433", lambda: _phase_tcp(server, 1433))
    await runner.run("tls_1433", lambda: _phase_tls(server, 1433))

    async def odbc_connect() -> str:
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
        return f"odbc connected to {server}/{database}, SELECT 1 ok"

    await runner.run("odbc_select1", odbc_connect)


async def _probe_cosmos(runner: _PhaseRunner) -> None:
    enabled = os.getenv("USE_CHAT_HISTORY_ENABLED", "false").strip().lower() == "true"
    if not enabled:
        raise _SkippedProbe("USE_CHAT_HISTORY_ENABLED is false")

    account = os.getenv("AZURE_COSMOSDB_ACCOUNT")
    database = os.getenv("AZURE_COSMOSDB_DATABASE")
    container = os.getenv("AZURE_COSMOSDB_CONVERSATIONS_CONTAINER")
    if not (account and database and container):
        raise _SkippedProbe("Cosmos account/database/container env vars not set")

    host = f"{account}.documents.azure.com"
    endpoint = f"https://{host}:443/"

    await runner.run("dns", lambda: _phase_dns(host))
    await runner.run("tcp_443", lambda: _phase_tcp(host, 443))
    await runner.run("tls_443", lambda: _phase_tls(host, 443))

    # Acquire an AAD token specifically for Cosmos so a 401/403 is
    # distinguishable from a 404/network error.
    from helpers.azure_credential_utils import get_azure_credential_async  # noqa: WPS433
    client_id = os.getenv("AZURE_CLIENT_ID") or None

    credential_holder: dict[str, Any] = {}

    async def acquire_token() -> str:
        credential = await get_azure_credential_async(client_id=client_id)
        credential_holder["credential"] = credential
        token = await credential.get_token("https://cosmos.azure.com/.default")
        return f"acquired AAD token (expires_on={token.expires_on})"

    await runner.run("aad_token", acquire_token)

    async def read_database() -> str:
        from azure.cosmos.aio import CosmosClient  # noqa: WPS433
        from azure.cosmos.exceptions import (  # noqa: WPS433
            CosmosHttpResponseError,
            CosmosResourceNotFoundError,
        )
        credential = credential_holder["credential"]
        async with CosmosClient(endpoint, credential=credential) as client:
            db = client.get_database_client(database)
            try:
                await db.read()
            except CosmosResourceNotFoundError as exc:
                raise RuntimeError(
                    f"database '{database}' returned 404 — check the database name "
                    f"in AZURE_COSMOSDB_DATABASE (current value resolves to "
                    f"'{database}'); raw error: {exc.message or exc}"
                ) from exc
            except CosmosHttpResponseError as exc:
                raise RuntimeError(
                    f"Cosmos HTTP {exc.status_code}: {exc.message or exc}"
                ) from exc
        return f"database '{database}' read ok at {_redact_endpoint(endpoint)}"

    await runner.run("read_database", read_database)

    async def read_container() -> str:
        from azure.cosmos.aio import CosmosClient  # noqa: WPS433
        from azure.cosmos.exceptions import (  # noqa: WPS433
            CosmosHttpResponseError,
            CosmosResourceNotFoundError,
        )
        credential = credential_holder["credential"]
        async with CosmosClient(endpoint, credential=credential) as client:
            db = client.get_database_client(database)
            cont = db.get_container_client(container)
            try:
                await cont.read()
            except CosmosResourceNotFoundError as exc:
                raise RuntimeError(
                    f"container '{container}' not found in database '{database}'; "
                    f"raw: {exc.message or exc}"
                ) from exc
            except CosmosHttpResponseError as exc:
                raise RuntimeError(
                    f"Cosmos HTTP {exc.status_code}: {exc.message or exc}"
                ) from exc
        return f"container '{container}' read ok"

    await runner.run("read_container", read_container)

    # Best-effort credential cleanup. Failure here is harmless (logged at INFO).
    credential = credential_holder.get("credential")
    if credential is not None and hasattr(credential, "close"):
        try:
            await credential.close()
        except Exception:
            logger.info("cosmos probe: credential.close() raised", exc_info=True)


async def _probe_ai_search(runner: _PhaseRunner) -> None:
    endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
    index = os.getenv("AZURE_AI_SEARCH_INDEX")
    if not endpoint:
        raise _SkippedProbe("AZURE_AI_SEARCH_ENDPOINT not set")

    parsed = urlparse(endpoint)
    host = parsed.hostname or ""
    if not host:
        raise _SkippedProbe(f"AZURE_AI_SEARCH_ENDPOINT not parseable: {endpoint!r}")

    await runner.run("dns", lambda: _phase_dns(host))
    await runner.run("tcp_443", lambda: _phase_tcp(host, 443))
    await runner.run("tls_443", lambda: _phase_tls(host, 443))

    if not index:
        return

    async def index_stats() -> str:
        # Use the public REST API directly with an AAD bearer token so
        # 401/403/404 are distinguishable from network errors.
        #
        # IMPORTANT: This probe must succeed with only the data-plane role the
        # backend actually needs at runtime ("Search Index Data Reader"). The
        # control-plane endpoint ``GET /indexes/{index}`` (which returns the
        # index definition) requires "Search Index Data Contributor" or
        # "Search Service Contributor" and returns 403 to a Reader. So we hit
        # a data-plane endpoint instead — ``POST /indexes/{index}/docs/search``
        # with ``top: 0`` returns no documents but proves the index exists and
        # is queryable by this identity, which is exactly what the chat code
        # needs.
        from helpers.azure_credential_utils import get_azure_credential_async  # noqa: WPS433
        import aiohttp  # noqa: WPS433

        client_id = os.getenv("AZURE_CLIENT_ID") or None
        credential = await get_azure_credential_async(client_id=client_id)
        try:
            token = await credential.get_token("https://search.azure.com/.default")
            url = (
                f"{endpoint.rstrip('/')}/indexes/{index}/docs/search"
                f"?api-version=2024-07-01"
            )
            headers = {
                "Authorization": f"Bearer {token.token}",
                "Content-Type": "application/json",
            }
            payload = {"search": "*", "top": 0, "count": True}
            timeout = aiohttp.ClientTimeout(total=_PHASE_TIMEOUT_SECONDS)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    body = await resp.text()
                    if resp.status >= 400:
                        raise RuntimeError(
                            f"POST /indexes/{index}/docs/search -> HTTP {resp.status}: {body[:300]}"
                        )
                    return f"index '{index}' queryable (HTTP {resp.status})"
        finally:
            if hasattr(credential, "close"):
                try:
                    await credential.close()
                except Exception:
                    logger.info("ai_search probe: credential.close() raised", exc_info=True)

    await runner.run("read_index", index_stats)


async def _probe_ai_foundry(runner: _PhaseRunner) -> None:
    endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
    if not endpoint:
        raise _SkippedProbe("AZURE_AI_AGENT_ENDPOINT not set")

    parsed = urlparse(endpoint)
    host = parsed.hostname or ""
    if not host:
        raise _SkippedProbe(f"AZURE_AI_AGENT_ENDPOINT not parseable: {endpoint!r}")

    await runner.run("dns", lambda: _phase_dns(host))
    await runner.run("tcp_443", lambda: _phase_tcp(host, 443))
    await runner.run("tls_443", lambda: _phase_tls(host, 443))

    async def list_deployments() -> str:
        from azure.ai.projects.aio import AIProjectClient  # noqa: WPS433
        from helpers.azure_credential_utils import get_azure_credential_async  # noqa: WPS433

        client_id = os.getenv("AZURE_CLIENT_ID") or None
        credential = await get_azure_credential_async(client_id=client_id)
        try:
            async with AIProjectClient(endpoint=endpoint, credential=credential) as client:
                count = 0
                async for _ in client.deployments.list():
                    count += 1
                    if count >= 50:  # safety cap; we only need to know it works
                        break
            return f"deployments.list ok ({count}{'+' if count >= 50 else ''} entries)"
        finally:
            if hasattr(credential, "close"):
                try:
                    await credential.close()
                except Exception:
                    logger.info("ai_foundry probe: credential.close() raised", exc_info=True)

    await runner.run("deployments_list", list_deployments)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

ALL_PROBES: list[tuple[str, Callable[[_PhaseRunner], Awaitable[None]]]] = [
    ("app_insights", _probe_app_insights),
    ("sql_database", _probe_sql),
    ("cosmos_db", _probe_cosmos),
    ("ai_search", _probe_ai_search),
    ("ai_foundry", _probe_ai_foundry),
]


async def run_all_probes() -> list[ProbeResult]:
    """Run every dependency probe sequentially and return their results.

    Never raises. Each probe's outcome is logged at INFO (ok) or ERROR
    (failed) with full phase-by-phase detail.
    """
    results: list[ProbeResult] = []
    for name, fn in ALL_PROBES:
        try:
            results.append(await _run_probe(name, fn))
        except Exception:  # noqa: BLE001 — last-resort guard
            logger.exception(
                "run_all_probes: catastrophic failure in probe %r — continuing",
                name,
            )
            results.append(ProbeResult(
                name=name, ok=False, duration_ms=0,
                detail="probe runner raised — see traceback above",
            ))
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
    logger.info("  cosmosdb_database     : %s", os.getenv("AZURE_COSMOSDB_DATABASE", "<unset>"))
    logger.info("  cosmosdb_container    : %s", os.getenv("AZURE_COSMOSDB_CONVERSATIONS_CONTAINER", "<unset>"))
    logger.info("  ai_search_endpoint    : %s", _redact_endpoint(os.getenv("AZURE_AI_SEARCH_ENDPOINT")))
    logger.info("  ai_search_index       : %s", os.getenv("AZURE_AI_SEARCH_INDEX", "<unset>"))
    logger.info("  ai_foundry_endpoint   : %s", _redact_endpoint(os.getenv("AZURE_AI_AGENT_ENDPOINT")))
    logger.info("  ai_foundry_model      : %s", os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME", "<unset>"))
    logger.info("  use_chat_history      : %s", os.getenv("USE_CHAT_HISTORY_ENABLED", "<unset>"))
    logger.info("=" * 72)
