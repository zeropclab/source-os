"""Tests for explicitly falsifiable ontology hypotheses."""


async def test_ontology_output_is_recorded_only_as_a_falsifiable_hypothesis(client):
    created = await client.post(
        "/api/ontology-hypotheses",
        json={
            "relationship_path": ["translator", "repeat-client context", "scattered terminology"],
            "source_material": "A translator describes searching old files for approved terms.",
            "counterexample": "Some translators already use a well-maintained glossary.",
            "unknowns": ["Whether the workaround is frequent enough to justify payment"],
            "smallest_validation_action": "Ask one repeat-client translator for a recent example.",
        },
    )

    assert created.status_code == 201
    assert created.json()["status"] == "hypothesis"
    listed = await client.get("/api/ontology-hypotheses")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["id"] == created.json()["id"]
