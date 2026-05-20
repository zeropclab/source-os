"""Web admin console — FastAPI sub-application with Jinja2 templates."""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

web_app = FastAPI(title="SourceOS Console")

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

from .routers import dashboard, sources as web_sources, items, jobs

web_app.include_router(dashboard.router)
web_app.include_router(web_sources.router)
web_app.include_router(items.router)
web_app.include_router(jobs.router)
