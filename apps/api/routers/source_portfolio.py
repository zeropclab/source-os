"""Source portfolio governance, deliberately separated from market-size assertions."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from apps.api.schemas.source_portfolio import (
    SourcePortfolioAssessmentCreate,
    SourcePortfolioAssessmentResponse,
)
from packages.storage.models.source import Source
from packages.storage.models.source_portfolio_assessment import SourcePortfolioAssessment

router = APIRouter()


def propose_action(body: SourcePortfolioAssessmentCreate) -> str:
    """A transparent routing heuristic, not a claim about market demand."""
    if body.technical_success_rate < 0.4:
        return "pause"
    if body.evidence_usefulness_rate < 0.5 and body.counterevidence_count > 0:
        return "counter_sample"
    if body.evidence_usefulness_rate >= 0.7 and body.downstream_decision_impact != "none recorded":
        return "add"
    return "reduce"


@router.post("/assessments", response_model=SourcePortfolioAssessmentResponse, status_code=201)
async def record_assessment(
    body: SourcePortfolioAssessmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    source = await db.scalar(select(Source.id).where(Source.id == body.source_id))
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    assessment = SourcePortfolioAssessment(
        **body.model_dump(), recommended_action=propose_action(body)
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


@router.get("")
async def get_portfolio(db: Annotated[AsyncSession, Depends(get_db)]):
    assessments = list(
        await db.scalars(
            select(SourcePortfolioAssessment).order_by(SourcePortfolioAssessment.created_at.desc())
        )
    )
    known_coverage = {
        "regions": sorted({item.region for item in assessments}),
        "languages": sorted({item.language for item in assessments}),
        "audiences": sorted({item.audience for item in assessments}),
        "evidence_types": sorted({item.evidence_type for item in assessments}),
    }
    return {
        "assessments": [
            SourcePortfolioAssessmentResponse.model_validate(item) for item in assessments
        ],
        "known_coverage": known_coverage,
        "mode_counts": {
            "exploration": sum(item.portfolio_mode == "exploration" for item in assessments),
            "exploitation": sum(item.portfolio_mode == "exploitation" for item in assessments),
        },
        "representativeness": "unknown",
        "coverage_warning": (
            "Known coverage only reflects assessed sources; unassessed regions, languages, "
            "audiences, and evidence types remain unknown."
        ),
    }
