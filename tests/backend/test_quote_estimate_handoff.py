from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _project(name: str = "Durable quote handoff") -> dict:
    response = client.post("/api/v1/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()


def _save_estimate(project: dict, *, duplicate_code: bool = False) -> dict:
    line_items = [
        {
            "code": "PIPE-001",
            "description": "Install PVC storm pipe",
            "item_type": "self_perform",
            "quantity": 120,
            "unit": "m",
            "production_rate_per_hour": 8,
            "labour": [{"role": "Pipe layer", "quantity": 1, "hourly_rate": 44}],
            "equipment": [{"name": "Excavator", "quantity": 1, "hourly_rate": 145}],
            "materials": [{"name": "Pipe allowance", "quantity": 120, "unit": "m", "unit_cost": 50}],
            "disposal": [],
            "vendor_quotes": [],
            "direct_unit_cost": 75,
            "notes": "Maintain installation scope.",
        }
    ]
    if duplicate_code:
        line_items.append(
            {
                **line_items[0],
                "description": "Duplicate pipe allowance",
            }
        )
    response = client.post(
        "/api/v1/estimates/workspace",
        json={
            "project_id": project["id"],
            "status": "draft",
            "estimate": {
                "project_name": project["name"],
                "project_code": "IH-PIPE-001",
                "line_items": line_items,
                "indirects": [{"description": "Mobilization", "amount": 5000}],
                "risks": [{"description": "Unknown utilities", "amount": 2000}],
                "markup": {"overhead_percent": 5, "profit_percent": 10},
                "assumptions": ["Normal access"],
                "exclusions": ["Contaminated soils"],
            },
        },
    )
    assert response.status_code == 201
    return response.json()


def _quote(project: dict, **overrides: object) -> dict:
    payload = {
        "project_id": project["id"],
        "supplier_name": "EMCO",
        "quote_reference": "EMCO-2026-44",
        "line_item_code": "PIPE-001",
        "line_item_description": "PVC storm pipe supply",
        "scope": "Supply PVC storm pipe",
        "scope_type": "material",
        "status": "received",
        "amount": 12500,
        "is_qualified": True,
        "qualification_notes": [],
        "is_selected": True,
        "exclusions": [],
    }
    payload.update(overrides)
    response = client.post("/api/v1/quotes", json=payload)
    assert response.status_code == 201
    return response.json()


def _handoff(project: dict):
    return client.post(
        "/api/v1/quotes/estimate-handoff",
        json={"project_id": project["id"]},
    )


def test_handoff_creates_auditable_draft_without_mutating_source_scope() -> None:
    project = _project()
    source = _save_estimate(project)
    quote = _quote(project)

    response = _handoff(project)

    assert response.status_code == 200
    result = response.json()
    assert result["created"] is True
    assert result["source_quote_ids"] == [quote["id"]]
    assert result["workspace"]["id"] != source["id"]
    assert result["workspace"]["status"] == "draft"
    snapshot = result["workspace"]["estimate"]
    estimate = snapshot["estimate"]
    line = estimate["line_items"][0]
    assert estimate["project_name"] == project["name"]
    assert estimate["project_code"] == "IH-PIPE-001"
    assert estimate["assumptions"] == ["Normal access"]
    assert estimate["exclusions"] == ["Contaminated soils"]
    assert line["description"] == "Install PVC storm pipe"
    assert line["quantity"] == 120
    assert line["unit"] == "m"
    assert line["labour"][0]["role"] == "Pipe layer"
    assert line["equipment"][0]["name"] == "Excavator"
    assert line["materials"] == []
    assert line["direct_unit_cost"] is None
    assert line["vendor_quotes"][0]["supplier"] == "EMCO"
    assert snapshot["source"] == "quote_estimate_handoff"
    assert snapshot["quote_handoff"]["source_workspace_id"] == source["id"]
    assert snapshot["quote_handoff"]["source_quote_ids"] == [quote["id"]]
    original = client.get(f"/api/v1/estimates/workspace/{source['id']}").json()
    assert original["estimate"]["estimate"]["line_items"][0]["vendor_quotes"] == []


def test_handoff_blocks_incomplete_saved_selection_without_creating_snapshot() -> None:
    project = _project("Blocked handoff")
    source = _save_estimate(project)
    _quote(project, amount=0, is_selected=False)

    response = _handoff(project)
    workspaces = client.get(
        f"/api/v1/estimates/workspace/project/{project['id']}"
    ).json()

    assert response.status_code == 409
    assert "handoff is blocked" in response.json()["error"]["message"]
    assert [item["id"] for item in workspaces["items"]] == [source["id"]]


def test_identical_handoff_is_idempotent() -> None:
    project = _project("Idempotent handoff")
    _save_estimate(project)
    _quote(project)

    first = _handoff(project).json()
    second = _handoff(project).json()
    workspaces = client.get(
        f"/api/v1/estimates/workspace/project/{project['id']}"
    ).json()

    assert first["created"] is True
    assert second["created"] is False
    assert second["workspace"]["id"] == first["workspace"]["id"]
    assert workspaces["total"] == 2


def test_handoff_rejects_duplicate_normalized_estimate_line_codes() -> None:
    project = _project("Ambiguous handoff")
    source = _save_estimate(project, duplicate_code=True)
    _quote(project, line_item_code=" pipe-001 ")

    response = _handoff(project)
    workspaces = client.get(
        f"/api/v1/estimates/workspace/project/{project['id']}"
    ).json()

    assert response.status_code == 409
    assert "duplicated" in response.json()["error"]["message"]
    assert [item["id"] for item in workspaces["items"]] == [source["id"]]
