"""Web admin console — FastAPI sub-application with Jinja2 templates."""

from fastapi import FastAPI

from .routers import dashboard, items, jobs, missions
from .routers import sources as web_sources

web_app = FastAPI(title="SourceOS Console")

web_app.include_router(dashboard.router)
web_app.include_router(web_sources.router)
web_app.include_router(missions.router)
web_app.include_router(items.router)
web_app.include_router(jobs.router)
