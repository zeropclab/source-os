"""Operator pages for defining a Need Issue from accepted evidence."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/needs", tags=["Web Needs"])
feature_router = APIRouter(prefix="/features", tags=["Web Features"])
product_thesis_router = APIRouter(prefix="/product-theses", tags=["Web Product Theses"])


@router.get("", response_class=HTMLResponse)
async def need_library(request: Request):
    return templates.TemplateResponse(request, "needs/list.html", {"title": "Need Library"})


@feature_router.get("/create", response_class=HTMLResponse)
async def create_feature_definition(request: Request):
    return templates.TemplateResponse(request, "features/create.html", {"title": "Define Feature"})


@feature_router.get("/{feature_id}/delivery", response_class=HTMLResponse)
async def feature_delivery_workbench(request: Request, feature_id: str):
    return templates.TemplateResponse(
        request,
        "features/delivery.html",
        {"title": "Review and Release Feature", "feature_id": feature_id},
    )


@product_thesis_router.get("/{thesis_id}", response_class=HTMLResponse)
async def product_thesis_workbench(request: Request, thesis_id: str):
    return templates.TemplateResponse(
        request,
        "product_theses/detail.html",
        {"title": "Decide Product Thesis", "thesis_id": thesis_id},
    )


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
