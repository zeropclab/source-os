"""Manual import of reality observations into the Evidence Inbox."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/observations", tags=["Web Manual Observations"])


@router.get("", response_class=HTMLResponse)
async def manual_observation_workbench(request: Request):
    return templates.TemplateResponse(
        request,
        "observations/create.html",
        {"title": "Record Reality Observation"},
    )
