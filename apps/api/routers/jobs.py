"""FetchJob status and retry endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db
from ..schemas.job import FetchJobResponse, FetchJobListResponse, RetryResponse
from packages.storage.models.fetch_job import FetchJob

router = APIRouter()


@router.get("", response_model=FetchJobListResponse)
async def list_jobs(
    status: str | None = Query(None),
    source_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(FetchJob)
    count_query = select(func.count(FetchJob.id))

    if status:
        query = query.where(FetchJob.status == status)
        count_query = count_query.where(FetchJob.status == status)
    if source_id:
        query = query.where(FetchJob.source_id == source_id)
        count_query = count_query.where(FetchJob.source_id == source_id)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(FetchJob.created_at.desc()).offset(offset).limit(page_size)
    )
    jobs = result.scalars().all()

    return FetchJobListResponse(items=jobs, total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=FetchJobResponse)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FetchJob).where(FetchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/retry", response_model=RetryResponse)
async def retry_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Re-queue a failed job for retry."""
    result = await db.execute(select(FetchJob).where(FetchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")

    # Create a new queued job referencing the failed one
    new_job = FetchJob(
        source_id=job.source_id,
        item_id=job.item_id,
        job_type=job.job_type,
        status="queued",
        retry_count=job.retry_count + 1,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    return RetryResponse(message="Job re-queued for retry", new_job_id=str(new_job.id))
