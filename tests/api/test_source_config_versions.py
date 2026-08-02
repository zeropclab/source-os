"""Behavior tests for immutable source configuration versions."""

from tests.factories import create_source


async def test_operator_can_create_new_source_config_without_rewriting_the_previous_version(
    client, db
):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )
    first_payload = {
        "access_mode": "public",
        "query_scope": {
            "query_terms": ["bug"],
            "filters": {"state": "open", "labels": ["bug"]},
        },
        "request_policy": {"request_limit": 2, "timeout_seconds": 10, "retry_limit": 1},
        "pagination_context_rules": {
            "page_limit": 1,
            "include_replies": True,
            "require_parent_context": True,
        },
        "extraction_settings": {
            "parser": "github_issue",
            "parser_version": "v1",
            "content_fields": ["title", "body", "comments"],
        },
    }
    second_payload = {
        **first_payload,
        "query_scope": {
            "query_terms": ["bug", "feedback"],
            "filters": {"state": "all"},
        },
    }

    first = await client.post(f"/api/sources/{source.id}/config-versions", json=first_payload)
    second = await client.post(f"/api/sources/{source.id}/config-versions", json=second_payload)
    retrieved_first = await client.get(f"/api/sources/{source.id}/config-versions/1")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2
    assert retrieved_first.status_code == 200
    assert retrieved_first.json() == first.json()
    assert retrieved_first.json()["query_scope"]["filters"] == {
        "state": "open",
        "labels": ["bug"],
    }


async def test_operator_can_review_the_newest_first_history_of_a_source_configuration(client, db):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )
    first_payload = {
        "access_mode": "public",
        "query_scope": {"query_terms": ["bug"]},
        "request_policy": {"request_limit": 2, "timeout_seconds": 10},
        "pagination_context_rules": {"page_limit": 1},
        "extraction_settings": {
            "parser": "github_issue",
            "parser_version": "v1",
            "content_fields": ["title"],
        },
    }
    second_payload = {
        **first_payload,
        "query_scope": {"query_terms": ["bug", "workaround"]},
        "request_policy": {"request_limit": 4, "timeout_seconds": 20},
    }

    first = await client.post(f"/api/sources/{source.id}/config-versions", json=first_payload)
    second = await client.post(f"/api/sources/{source.id}/config-versions", json=second_payload)
    history = await client.get(f"/api/sources/{source.id}/config-versions")

    assert first.status_code == 201
    assert second.status_code == 201
    assert history.status_code == 200
    assert history.json()["total"] == 2
    assert [item["version"] for item in history.json()["items"]] == [2, 1]
    assert history.json()["items"][0]["query_scope"]["query_terms"] == ["bug", "workaround"]


async def test_operator_cannot_publish_a_source_config_with_a_blank_query_scope(client, db):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )

    response = await client.post(
        f"/api/sources/{source.id}/config-versions",
        json={
            "access_mode": "public",
            "query_scope": {},
            "request_policy": {"request_limit": 2, "timeout_seconds": 10},
            "pagination_context_rules": {"page_limit": 1},
            "extraction_settings": {
                "parser": "github_issue",
                "parser_version": "v1",
                "content_fields": ["title"],
            },
        },
    )

    assert response.status_code == 422


async def test_operator_cannot_publish_a_source_config_with_a_zero_request_limit(client, db):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )

    response = await client.post(
        f"/api/sources/{source.id}/config-versions",
        json={
            "access_mode": "public",
            "query_scope": {"query_terms": ["bug"]},
            "request_policy": {"request_limit": 0, "timeout_seconds": 10},
            "pagination_context_rules": {"page_limit": 1},
            "extraction_settings": {
                "parser": "github_issue",
                "parser_version": "v1",
                "content_fields": ["title"],
            },
        },
    )

    assert response.status_code == 422


async def test_operator_cannot_publish_a_source_config_with_an_empty_filter_value(client, db):
    source = await create_source(
        db,
        name="GitHub public issues",
        platform="github",
        source_type="issues",
        url="https://github.com/example/public-project/issues",
    )

    response = await client.post(
        f"/api/sources/{source.id}/config-versions",
        json={
            "access_mode": "public",
            "query_scope": {"query_terms": ["bug"], "filters": {"labels": []}},
            "request_policy": {"request_limit": 2, "timeout_seconds": 10},
            "pagination_context_rules": {"page_limit": 1},
            "extraction_settings": {
                "parser": "github_issue",
                "parser_version": "v1",
                "content_fields": ["title"],
            },
        },
    )

    assert response.status_code == 422
