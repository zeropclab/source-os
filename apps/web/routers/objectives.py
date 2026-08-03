"""Web entry point for one Discovery Objective workspace."""

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/objectives", tags=["Web Discovery Objectives"])


@router.get("/{objective_id}", response_class=HTMLResponse)
async def discovery_objective_workspace(objective_id: uuid.UUID, request: Request):
    return templates.TemplateResponse(
        request,
        "objectives/workspace.html",
        {"title": "Discovery Objective", "objective_id": objective_id},
    )
