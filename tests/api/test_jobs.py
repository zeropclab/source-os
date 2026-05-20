"""Tests for jobs API."""

from tests.factories import create_source, create_item, create_job


async def test_list_jobs_empty(client):
    response = await client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_jobs_with_data(client, db):
    source = await create_source(db, name="S", url="https://example.com")
    await create_job(db, source_id=source.id, job_type="fetch", status="success")
    await create_job(db, source_id=source.id, job_type="fetch", status="failed", error_code="TIMEOUT")

    response = await client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2


async def test_filter_jobs_by_status(client, db):
    source = await create_source(db, name="S", url="https://example.com")
    await create_job(db, source_id=source.id, job_type="fetch", status="success")
    await create_job(db, source_id=source.id, job_type="fetch", status="failed")

    response = await client.get("/api/jobs?status=failed")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "failed"


async def test_retry_job(client, db):
    source = await create_source(db, name="S", url="https://example.com")
    item = await create_item(db, source.id, title="T", canonical_url="https://example.com/1")
    job = await create_job(db, source_id=source.id, item_id=item.id, job_type="fetch", status="failed")

    response = await client.post(f"/api/jobs/{job.id}/retry")
    assert response.status_code == 200
    data = response.json()
    assert "retry" in data["message"].lower() or data["job_type"] == "fetch"
