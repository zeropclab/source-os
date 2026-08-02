"""Operator pages for defining a Need Issue from accepted evidence."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/needs", tags=["Web Needs"])
feature_router = APIRouter(prefix="/features", tags=["Web Features"])


@feature_router.get("/create", response_class=HTMLResponse)
async def create_feature_definition(request: Request):
    return templates.TemplateResponse(request, "features/create.html", {"title": "Define Feature"})


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


@router.get("/experiments/{experiment_id}", response_class=HTMLResponse)
async def experiment_decision_workbench(request: Request, experiment_id: str):
    return templates.TemplateResponse(
        request,
        "needs/experiment.html",
        {"title": "Run Validation Experiment", "experiment_id": experiment_id},
    )
