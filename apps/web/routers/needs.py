"""Operator pages for defining a Need Issue from accepted evidence."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/needs", tags=["Web Needs"])


@router.get("/create", response_class=HTMLResponse)
async def create_need_from_signal(request: Request):
    return templates.TemplateResponse(
        request,
        "needs/create_from_signal.html",
        {"title": "Define Need Issue"},
    )


@router.get("/{need_issue_id}", response_class=HTMLResponse)
async def need_validation_workbench(request: Request, need_issue_id: str):
    return templates.TemplateResponse(
        request,
        "needs/detail.html",
        {"title": "Validate Need Issue", "need_issue_id": need_issue_id},
    )
