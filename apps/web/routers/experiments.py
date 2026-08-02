"""Operator library for reopening reality-facing validation experiments."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/experiments", tags=["Web Experiments"])


@router.get("", response_class=HTMLResponse)
async def experiment_library(request: Request):
    return templates.TemplateResponse(
        request, "experiments/list.html", {"title": "Validation Experiment Library"}
    )
