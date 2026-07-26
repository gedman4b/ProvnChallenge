"""ASGI entrypoint: mounts the REST API and the MCP streamable-HTTP app on
one process so both transports share the same downstream client instances,
circuit breakers, and structured logging (see app/dependencies.py).

Run locally with: uvicorn app.main:app --reload
MCP endpoint: POST/GET http://localhost:8000/mcp
REST endpoints: http://localhost:8000/health, /v1/recommendations/{id}, ...
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router as rest_router
from app.logging_config import configure_logging, get_logger
from app.mcp_server import mcp

configure_logging()
logger = get_logger(__name__)

mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("service_starting")
    async with mcp.session_manager.run():
        yield
    logger.info("service_stopping")


app = FastAPI(
    title="arrivia Agentic Travel Recommendations API",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(rest_router)
app.mount("/mcp", mcp_app)
