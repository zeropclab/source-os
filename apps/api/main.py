"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apps.web.main import web_app

from .config import settings
from .routers import export, health, items, jobs, need_issues, sources

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
app.include_router(items.router, prefix="/api/items", tags=["Items"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(need_issues.router, prefix="/api/need-issues", tags=["Need Issues"])

# Static files and Web UI
app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")
app.mount("/", web_app)
