"""Web items browser router."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..main import templates

router = APIRouter(prefix="/items", tags=["Web Items"])


@router.get("", response_class=HTMLResponse)
async def item_list(request: Request):
    return templates.TemplateResponse(request, "items/list.html", {"title": "Items"})


@router.get("/{item_id}", response_class=HTMLResponse)
async def item_detail(request: Request, item_id: str):
    return templates.TemplateResponse(request, "items/detail.html", {"item_id": item_id, "title": "Item Detail"})
