"""Operator page for falsifiable ontology hypotheses."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..templating import templates

router = APIRouter(prefix="/ontology", tags=["Web Ontology Hypotheses"])


@router.get("", response_class=HTMLResponse)
async def ontology_hypothesis_workbench(request: Request):
    return templates.TemplateResponse(
        request,
        "ontology/workbench.html",
        {"title": "Explore Ontology Hypotheses"},
    )
