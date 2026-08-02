"""Web admin console — FastAPI sub-application with Jinja2 templates."""

from fastapi import FastAPI

from .routers import (
    agents,
    dashboard,
    experiments,
    items,
    jobs,
    missions,
    needs,
    observations,
    ontology,
    portfolio,
)
from .routers import sources as web_sources

web_app = FastAPI(title="SourceOS Console")

web_app.include_router(dashboard.router)
web_app.include_router(experiments.router)
web_app.include_router(web_sources.router)
web_app.include_router(missions.router)
web_app.include_router(observations.router)
web_app.include_router(agents.router)
web_app.include_router(ontology.router)
web_app.include_router(portfolio.router)
web_app.include_router(needs.router)
web_app.include_router(needs.feature_router)
web_app.include_router(needs.product_thesis_router)
web_app.include_router(items.router)
web_app.include_router(jobs.router)
