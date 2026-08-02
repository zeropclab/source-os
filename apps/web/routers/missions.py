"""Operator workbench for bounded evidence acquisition missions."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/missions", tags=["Web Missions"])


@router.get("", response_class=HTMLResponse)
async def mission_workbench(request: Request):
    return templates.TemplateResponse(
        request,
        "missions/workbench.html",
        {"title": "Mission Workbench"},
    )
