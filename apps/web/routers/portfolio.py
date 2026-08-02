"""Operator page for source portfolio calibration."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/portfolio", tags=["Web Source Portfolio"])


@router.get("", response_class=HTMLResponse)
async def source_portfolio_workbench(request: Request):
    return templates.TemplateResponse(
        request,
        "portfolio/workbench.html",
        {"title": "Review Source Portfolio"},
    )
