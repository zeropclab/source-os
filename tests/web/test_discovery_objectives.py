"""Public page contract for the Discovery Objective workspace."""


async def test_objective_workspace_page_loads_the_durable_workspace_contract(client):
    response = await client.get("/objectives/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    page = response.text
    assert 'id="objective-workspace"' in page
    assert 'id="objective-status"' in page
    assert "/api/discovery-objectives/${objectiveId}/workspace" in page
    assert "Approved collection boundary" in page
    assert "pending_approvals" in page
    assert "boundary_revisions" in page
    assert "workspace.plans" in page
