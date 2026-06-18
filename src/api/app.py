"""
FastAPI application entry point for the Conversation Knowledge Mining Solution Accelerator.

This module sets up the FastAPI app, configures middleware, loads environment variables,
and registers API routers.

Logging strategy
----------------
* Logging is configured **before** any other import so that even crashes during
  router / service import are visible in stdout / Azure App Service Log stream.
* The very first lines after the docstring are unconditional ``print`` calls to
  ``stderr`` — these run even if ``logging`` itself fails to configure, which
  guarantees that "container started but you see nothing" never happens silently.
* Every heavy import is wrapped in ``try`` / ``except`` and re-raised with a
  descriptive message so that the failing module is unambiguous in the logs.
* On application startup, a lifespan handler runs ``run_all_probes`` against
  every external dependency (SQL DB, Cosmos DB, Azure AI Search, Azure AI
  Foundry, Application Insights). Failures are logged but do **not** prevent
  the app from starting — this way ``/health`` and ``/health/ready`` stay
  reachable for diagnostics.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Earliest-possible breadcrumbs — run before any third-party import.
# ---------------------------------------------------------------------------
import sys as _sys

print("[app.py] module import starting", file=_sys.stderr, flush=True)

import logging
import os
import sys
import traceback
from contextlib import asynccontextmanager

# Force unbuffered stdout / stderr in containers even if PYTHONUNBUFFERED was
# not set on the image. Without this, Python may buffer log lines and the
# Azure Log stream appears empty for long stretches.
try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except Exception:  # pragma: no cover — older Python or non-TTY streams
    pass


# ---------------------------------------------------------------------------
# Logging configuration — must happen before any module that may emit logs.
# ---------------------------------------------------------------------------
AZURE_BASIC_LOGGING_LEVEL = os.getenv("AZURE_BASIC_LOGGING_LEVEL", "INFO").upper()
AZURE_PACKAGE_LOGGING_LEVEL = os.getenv("AZURE_PACKAGE_LOGGING_LEVEL", "WARNING").upper()
AZURE_LOGGING_PACKAGES = [
    pkg.strip() for pkg in os.getenv("AZURE_LOGGING_PACKAGES", "").split(",") if pkg.strip()
]

logging.basicConfig(
    level=getattr(logging, AZURE_BASIC_LOGGING_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)

# Suppress noisy Azure SDK and OpenTelemetry internal loggers.
for noisy in (
    "azure.core.pipeline.policies.http_logging_policy",
    "azure.core.pipeline.policies._universal",
    "azure.cosmos",
    "opentelemetry.sdk",
    "azure.monitor.opentelemetry.exporter.export._base",
):
    logging.getLogger(noisy).setLevel(logging.WARNING)

for logger_name in AZURE_LOGGING_PACKAGES:
    logging.getLogger(logger_name).setLevel(
        getattr(logging, AZURE_PACKAGE_LOGGING_LEVEL, logging.WARNING)
    )

logger = logging.getLogger("app")
logger.info("[app.py] logging configured at level=%s", AZURE_BASIC_LOGGING_LEVEL)


# ---------------------------------------------------------------------------
# Defensive imports — wrap each so we know exactly which one fails on startup.
# ---------------------------------------------------------------------------
def _safe_import(label: str, importer):
    """Run ``importer`` and log+re-raise with a descriptive prefix on failure."""
    try:
        logger.info("[app.py] importing %s", label)
        return importer()
    except Exception as exc:
        logger.critical(
            "[app.py] FAILED to import %s: %s: %s\n%s",
            label,
            type(exc).__name__,
            exc,
            traceback.format_exc(),
        )
        raise


from dotenv import load_dotenv  # noqa: E402

load_dotenv()
logger.info("[app.py] .env loaded (if present)")

FastAPI = _safe_import("fastapi", lambda: __import__("fastapi", fromlist=["FastAPI"]).FastAPI)
CORSMiddleware = _safe_import(
    "fastapi.middleware.cors",
    lambda: __import__("fastapi.middleware.cors", fromlist=["CORSMiddleware"]).CORSMiddleware,
)
uvicorn = _safe_import("uvicorn", lambda: __import__("uvicorn"))

backend_router = _safe_import(
    "api.api_routes",
    lambda: __import__("api.api_routes", fromlist=["router"]).router,
)
history_router = _safe_import(
    "api.history_routes",
    lambda: __import__("api.history_routes", fromlist=["router"]).router,
)
drill_router = _safe_import(
    "api.drill_routes",
    lambda: __import__("api.drill_routes", fromlist=["router"]).router,
)
audio_router = _safe_import(
    "api.audio_routes",
    lambda: __import__("api.audio_routes", fromlist=["router"]).router,
)

configure_azure_monitor = _safe_import(
    "azure.monitor.opentelemetry",
    lambda: __import__(
        "azure.monitor.opentelemetry", fromlist=["configure_azure_monitor"]
    ).configure_azure_monitor,
)
FastAPIInstrumentor = _safe_import(
    "opentelemetry.instrumentation.fastapi",
    lambda: __import__(
        "opentelemetry.instrumentation.fastapi", fromlist=["FastAPIInstrumentor"]
    ).FastAPIInstrumentor,
)

from common.logging.span_filters import (  # noqa: E402
    DropASGIResponseBodySpanProcessor,
    DropCosmosDependencySpanProcessor,
)
from common.logging.startup_checks import (  # noqa: E402
    log_startup_banner,
    run_all_probes,
)


APP_VERSION = "1.0.0"


import asyncio  # noqa: E402

# ---------------------------------------------------------------------------
# Lifespan handler — kicks dependency probes off in the background so they
# never block uvicorn from binding the port. Blocking startup work here is
# what caused `SiteStartupCancelled` on Azure App Service.
# ---------------------------------------------------------------------------
async def _run_startup_probes_background(fastapi_app) -> None:
    try:
        results = await run_all_probes()
    except Exception:
        logger.exception("[app.py] startup probes raised unexpectedly")
        results = []

    failed = [r for r in results if not r.ok]
    skipped = [r for r in results if r.skipped]
    passed = [r for r in results if r.ok and not r.skipped]
    logger.info(
        "[app.py] startup probes complete: %d passed, %d skipped, %d failed",
        len(passed),
        len(skipped),
        len(failed),
    )
    if failed:
        logger.error(
            "[app.py] failing dependencies at startup: %s",
            ", ".join(f"{r.name} ({r.detail})" for r in failed),
        )

    fastapi_app.state.startup_probe_results = [r.to_dict() for r in results]


@asynccontextmanager
async def lifespan(_fastapi_app):
    log_startup_banner(APP_VERSION)
    # Initialize the cache so /health/startup never errors before probes finish.
    _fastapi_app.state.startup_probe_results = None
    # Kick off probes in the background. The app starts serving immediately;
    # probe results stream into the log as each dependency responds, and are
    # exposed via /health/startup and /health/ready.
    probe_task = asyncio.create_task(
        _run_startup_probes_background(_fastapi_app),
        name="startup-dependency-probes",
    )
    logger.info("[app.py] startup probes launched in background; app is ready to serve")
    try:
        yield
    finally:
        if not probe_task.done():
            probe_task.cancel()
        logger.info("[app.py] shutdown complete")


def build_app() -> "FastAPI":
    """Creates and configures the FastAPI application instance."""
    fastapi_app = FastAPI(
        title="Conversation Knowledge Mining Solution Accelerator",
        version=APP_VERSION,
        lifespan=lifespan,
    )

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    fastapi_app.include_router(backend_router, prefix="/api", tags=["backend"])
    fastapi_app.include_router(history_router, prefix="/history", tags=["history"])
    fastapi_app.include_router(drill_router, prefix="/api/drill", tags=["drill"])
    fastapi_app.include_router(audio_router, prefix="/api/audio", tags=["audio"])

    @fastapi_app.get("/health")
    async def health_check():
        """Liveness probe — always returns 200 if the process is running."""
        return {"status": "healthy", "version": APP_VERSION}

    @fastapi_app.get("/health/ready")
    async def readiness_check():
        """Deep readiness probe — re-runs all dependency probes on demand."""
        results = await run_all_probes()
        payload = {
            "status": "ready" if all(r.ok for r in results) else "degraded",
            "version": APP_VERSION,
            "probes": [r.to_dict() for r in results],
        }
        return payload

    @fastapi_app.get("/health/startup")
    async def startup_results():
        """Returns the dependency probe results captured at app startup.

        Probes run in the background to avoid blocking port binding, so this
        endpoint may report ``running`` for a short window after the container
        starts.
        """
        cached = getattr(fastapi_app.state, "startup_probe_results", None)
        if cached is None:
            return {"status": "running", "version": APP_VERSION, "probes": []}
        return {"status": "ok", "version": APP_VERSION, "probes": cached}

    instrumentation_key = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if instrumentation_key:
        try:
            configure_azure_monitor(
                connection_string=instrumentation_key,
                enable_live_metrics=True,
                span_processors=[
                    DropASGIResponseBodySpanProcessor(),
                    DropCosmosDependencySpanProcessor(),
                ],
            )
            FastAPIInstrumentor.instrument_app(fastapi_app, excluded_urls="health")
            logger.info(
                "[app.py] Application Insights configured (live metrics + FastAPI instrumentation)"
            )
        except Exception:
            logger.exception(
                "[app.py] FAILED to configure Application Insights — continuing without telemetry"
            )
    else:
        logger.warning(
            "[app.py] APPLICATIONINSIGHTS_CONNECTION_STRING not set — telemetry disabled"
        )

    return fastapi_app


try:
    app = build_app()
    logger.info("[app.py] FastAPI app built successfully — ready to serve")
except Exception:
    logger.critical("[app.py] FATAL: build_app() raised — process will exit")
    logger.critical("[app.py] traceback:\n%s", traceback.format_exc())
    raise


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

