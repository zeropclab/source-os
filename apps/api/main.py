"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.web.main import web_app

from .config import settings
from .routers import (
    acquisition_mission_runs,
    acquisition_missions,
    agent_runs,
    delivery_records,
    experiments,
    export,
    external_signals,
    feature_outcomes,
    health,
    items,
    jobs,
    need_issues,
    product_theses,
    source_config_versions,
    source_probe_runs,
    sources,
    today,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SourceOS API starting", host=settings.api_host, port=settings.api_port)
    yield
    logger.info("SourceOS API shutting down")


app = FastAPI(
    title="SourceOS API",
    description="信源作业系统 — 多平台信源监测、采集、内容提取和知识导出",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(health.router, tags=["Health"])
app.include_router(sources.router, prefix="/api/sources", tags=["Sources"])
app.include_router(
    source_config_versions.router,
    prefix="/api/sources",
    tags=["Source Configuration Versions"],
)
app.include_router(
    source_probe_runs.router,
    prefix="/api/sources",
    tags=["Source Probes"],
)
app.include_router(
    source_probe_runs.read_router,
    prefix="/api/source-probes",
    tags=["Source Probes"],
)
app.include_router(items.router, prefix="/api/items", tags=["Items"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(need_issues.router, prefix="/api/need-issues", tags=["Need Issues"])
app.include_router(agent_runs.router, prefix="/api/agent-runs", tags=["Agent Runs"])
app.include_router(experiments.router, prefix="/api/experiments", tags=["Validation Experiments"])
app.include_router(product_theses.router, prefix="/api/product-theses", tags=["Product Theses"])
app.include_router(
    delivery_records.router, prefix="/api/delivery-records", tags=["Delivery Evidence"]
)
app.include_router(
    feature_outcomes.router, prefix="/api/feature-outcomes", tags=["Feature Outcomes"]
)
app.include_router(today.router, prefix="/api/today", tags=["Today"])
app.include_router(
    acquisition_missions.router,
    prefix="/api/acquisition-missions",
    tags=["Acquisition Missions"],
)
app.include_router(
    acquisition_mission_runs.router,
    prefix="/api/acquisition-missions",
    tags=["Acquisition Mission Runs"],
)
app.include_router(
    acquisition_mission_runs.read_router,
    prefix="/api/acquisition-mission-runs",
    tags=["Acquisition Mission Runs"],
)
app.include_router(
    external_signals.router, prefix="/api/external-signals", tags=["External Signals"]
)
app.include_router(
    external_signals.inbox_router,
    prefix="/api/evidence-inbox",
    tags=["Evidence Inbox"],
)

# Static files and Web UI
app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")
app.mount("/", web_app)
