"""NEXORA ERP — FastAPI Application Entrypoint."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import (
    auth,
    hr,
    inventory,
    operations_ai,
    organizations,
    procurement,
    sales_finance,
)
from app import ui_portal
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.exceptions import NexoraError
from app.core.logging import correlation_id_ctx, logger
from app.services.seed_service import seed_demo_data


def initialize_database_and_seed() -> None:
    """Create schema tables and idempotently seed Nexora Demo Holdings."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_result = seed_demo_data(db)
        logger.info("NEXORA ERP Database initialized: %s", seed_result)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database_and_seed()
    yield


app = FastAPI(
    title="NEXORA ERP — AI-Powered Enterprise Resource Planning Platform",
    description="Enterprise Multi-Tenant ERP with Double-Entry Accounting, Weighted-Average Inventory, Workflow Engine, and Nexora Intelligence.",
    version="1.0.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or f"req-{uuid.uuid4().hex[:12]}"
    token = correlation_id_ctx.set(cid)
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
    finally:
        correlation_id_ctx.reset(token)


@app.exception_handler(NexoraError)
async def nexora_exception_handler(request: Request, exc: NexoraError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "correlation_id": correlation_id_ctx.get(),
                "details": exc.details,
            }
        },
    )


@app.get(f"{settings.api_v1_prefix}/health", tags=["System"])
def health_check() -> dict:
    return {
        "status": "healthy",
        "application": settings.app_name,
        "version": "1.0.0",
        "default_currency": settings.default_currency,
        "default_timezone": settings.default_timezone,
    }


app.include_router(ui_portal.router)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(organizations.router, prefix=settings.api_v1_prefix)
app.include_router(hr.router, prefix=settings.api_v1_prefix)
app.include_router(inventory.router, prefix=settings.api_v1_prefix)
app.include_router(procurement.router, prefix=settings.api_v1_prefix)
app.include_router(sales_finance.router, prefix=settings.api_v1_prefix)
app.include_router(operations_ai.router, prefix=settings.api_v1_prefix)


@app.websocket(f"{settings.api_v1_prefix}/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "type": "CONNECTED",
                "message": "Connected to NEXORA ERP Real-Time Telemetry Bus",
                "timestamp": "live",
            }
        )
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "ACK", "echo": data})
    except WebSocketDisconnect:
        pass
