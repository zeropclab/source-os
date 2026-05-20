"""Tests for items API."""

from tests.factories import create_source, create_item


async def test_list_items_empty(client):
    response = await client.get("/api/items")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_items_with_data(client, db):
    source = await create_source(db, name="Test Source", url="https://example.com")
    await create_item(db, source.id, title="Item 1", canonical_url="https://example.com/1")
    await create_item(db, source.id, title="Item 2", canonical_url="https://example.com/2")

    response = await client.get("/api/items")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_filter_items_by_source(client, db):
    s1 = await create_source(db, name="S1", url="https://a.com")
    s2 = await create_source(db, name="S2", url="https://b.com")
    await create_item(db, s1.id, title="From S1", canonical_url="https://a.com/1")
    await create_item(db, s2.id, title="From S2", canonical_url="https://b.com/1")

    response = await client.get(f"/api/items?source_id={s1.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


async def test_filter_items_by_status(client, db):
    source = await create_source(db, name="S", url="https://example.com")
    await create_item(db, source.id, title="New", status="discovered", canonical_url="https://example.com/1")
    await create_item(db, source.id, title="Done", status="extracted", canonical_url="https://example.com/2")

    response = await client.get("/api/items?status=extracted")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "extracted"


async def test_get_item_not_found(client):
    response = await client.get("/api/items/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
