"""Web jobs monitor router."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/jobs", tags=["Web Jobs"])


@router.get("", response_class=HTMLResponse)
async def job_list(request: Request):
    return templates.TemplateResponse(request, "jobs/list.html", {"title": "Jobs"})
