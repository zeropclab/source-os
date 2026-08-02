"""Web source management router."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/sources", tags=["Web Sources"])


@router.get("", response_class=HTMLResponse)
async def source_list(request: Request):
    return templates.TemplateResponse(request, "sources/list.html", {"title": "Sources"})


@router.get("/create", response_class=HTMLResponse)
async def source_create_form(request: Request):
    return templates.TemplateResponse(request, "sources/create.html", {"title": "Add Source"})


@router.get("/{source_id}", response_class=HTMLResponse)
async def source_detail(request: Request, source_id: str):
    return templates.TemplateResponse(
        request,
        "sources/detail.html",
        {"source_id": source_id, "title": "Source Detail"},
    )
