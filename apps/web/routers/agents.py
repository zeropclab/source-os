"""Operator pages for bounded Pi Agent proposal runs."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/agents", tags=["Web Agent Runs"])


@router.get("", response_class=HTMLResponse)
async def create_agent_run_workbench(request: Request):
    return templates.TemplateResponse(request, "agents/create.html", {"title": "Run Pi Agent"})


@router.get("/{run_id}", response_class=HTMLResponse)
async def agent_run_detail_workbench(request: Request, run_id: str):
    return templates.TemplateResponse(
        request,
        "agents/detail.html",
        {"title": "Review Pi Agent Run", "run_id": run_id},
    )
