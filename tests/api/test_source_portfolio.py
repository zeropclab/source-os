"""Source portfolio governance keeps collection quality separate from volume."""

from tests.factories import create_source


async def test_portfolio_assessment_exposes_known_coverage_without_claiming_representativeness(
    client, db
):
    source = await create_source(db, name="Indonesian marketplace sellers")
    response = await client.post(
        "/api/source-portfolio/assessments",
        json={
            "source_id": str(source.id),
            "region": "Indonesia",
            "language": "id",
            "audience": "marketplace_sellers",
            "evidence_type": "public_comments",
            "portfolio_mode": "exploration",
            "technical_success_rate": 0.92,
            "context_completeness_rate": 0.71,
            "evidence_usefulness_rate": 0.38,
            "independent_evidence_count": 6,
            "counterevidence_count": 3,
            "estimated_cost_cents": 120,
            "downstream_decision_impact": "informed a source expansion decision",
            "rationale": (
                "Useful evidence is below the exploration bar and needs a contrasting source."
            ),
        },
    )

    assert response.status_code == 201
    portfolio = await client.get("/api/source-portfolio")
    assert portfolio.status_code == 200
    data = portfolio.json()
    assert data["known_coverage"]["regions"] == ["Indonesia"]
    assert data["assessments"][0]["recommended_action"] == "counter_sample"
    assert data["representativeness"] == "unknown"
    assert "unassessed" in data["coverage_warning"]


async def test_portfolio_rejects_unsupported_source_quality_claim(client, db):
    source = await create_source(db)
    response = await client.post(
        "/api/source-portfolio/assessments",
        json={
            "source_id": str(source.id),
            "region": "Latin America",
            "language": "es",
            "audience": "independent_developers",
            "evidence_type": "forum_threads",
            "portfolio_mode": "exploitation",
            "technical_success_rate": 1.2,
            "context_completeness_rate": 0.5,
            "evidence_usefulness_rate": 0.5,
            "independent_evidence_count": 0,
            "counterevidence_count": 0,
            "estimated_cost_cents": 0,
            "downstream_decision_impact": "none recorded",
            "rationale": "The assertion is intentionally invalid.",
        },
    )
    assert response.status_code == 422
