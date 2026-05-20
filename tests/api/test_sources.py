"""Tests for sources CRUD API."""

from tests.factories import create_source


async def test_list_sources_empty(client):
    response = await client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_sources_with_data(client, db):
    await create_source(db, name="Source 1", url="https://example.com/1")
    await create_source(db, name="Source 2", url="https://example.com/2")

    response = await client.get("/api/sources")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_create_source(client, db):
    payload = {
        "name": "Test RSS",
        "platform": "rss",
        "source_type": "rss_feed",
        "url": "https://example.com/rss",
    }
    response = await client.post("/api/sources", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test RSS"
    assert data["platform"] == "rss"
    assert data["status"] == "active"
    assert data["id"] is not None


async def test_get_source(client, db):
    source = await create_source(db, name="Detail Source")

    response = await client.get(f"/api/sources/{source.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Detail Source"
    assert data["id"] == str(source.id)


async def test_get_source_not_found(client):
    response = await client.get("/api/sources/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_update_source(client, db):
    source = await create_source(db, name="Original Name")

    response = await client.patch(f"/api/sources/{source.id}", json={"name": "Updated Name"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"


async def test_delete_source(client, db):
    source = await create_source(db, name="To Delete")

    response = await client.delete(f"/api/sources/{source.id}")
    assert response.status_code == 204

    response = await client.get(f"/api/sources/{source.id}")
    assert response.status_code == 404


async def test_filter_sources_by_platform(client, db):
    await create_source(db, name="RSS 1", platform="rss", url="https://a.com")
    await create_source(db, name="Web", platform="website", url="https://b.com")

    response = await client.get("/api/sources?platform=rss")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["platform"] == "rss"


async def test_filter_sources_by_status(client, db):
    await create_source(db, name="Active", status="active", url="https://a.com")
    await create_source(db, name="Paused", status="paused", url="https://b.com")

    response = await client.get("/api/sources?status=paused")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "paused"
