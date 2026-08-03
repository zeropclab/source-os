"""A deliberately small daily cockpit for reality-facing work."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_db
from packages.storage.models.need_issue import (
    DeliveryRecord,
    FeatureOutcome,
    NeedIssue,
    ValidationExperiment,
)

router = APIRouter()


@router.get("")
async def today_workspace(db: Annotated[AsyncSession, Depends(get_db)]):
    active_validation = await db.scalar(
        select(ValidationExperiment)
        .where(ValidationExperiment.status == "running")
        .order_by(ValidationExperiment.updated_at.asc(), ValidationExperiment.id.asc())
        .limit(1)
    )
    need = await db.scalar(
        select(NeedIssue)
        .where(
            NeedIssue.status.in_(["captured", "triaged", "evidence-backed", "discovery-validated"])
        )
        .order_by(NeedIssue.updated_at.asc())
        .limit(1)
    )
    validations = await db.scalar(
        select(func.count(ValidationExperiment.id)).where(
            ValidationExperiment.status.in_(["draft", "approved", "running"])
        )
    )
    builds = await db.scalar(
        select(func.count(DeliveryRecord.id)).where(DeliveryRecord.status == "in-development")
    )
    outcomes = await db.scalar(select(func.count(FeatureOutcome.id)))
    if active_validation is not None:
        next_reality_action = (
            "A running validation experiment has priority: record a real response, refusal, "
            "or deadline silence. Do not send unplanned follow-ups or create a Product Thesis."
        )
    else:
        next_reality_action = (
            need.next_validation_action if need else "Import one concrete observation."
        )
    return {
        "next_reality_action": next_reality_action,
        "strongest_objection": (need.counterevidence_summary if need else None)
        or "Evidence is insufficient; do not infer an opportunity.",
        "active_need": None
        if need is None
        else {"id": need.id, "title": need.title, "unknowns": need.unknowns},
        "active_validation": None
        if active_validation is None
        else {
            "id": active_validation.id,
            "status": active_validation.status,
            "stop_condition": active_validation.stop_condition,
        },
        "wip": {
            "validations": {"active": validations or 0, "limit": 3},
            "builds_or_paid_pilots": {"active": builds or 0, "limit": 1},
        },
        "recorded_outcomes": outcomes or 0,
    }
