import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/bennett-staging-procurement-plan.yml"
MARKER = ROOT / "ops/staging-pilots/2026-08-28-bennett-procurement-plan.json"
PROCUREMENT_TOOL = ROOT / "backend/app/tools/bennett_procurement_staging_pilot.py"


def test_workflow_runs_only_after_exact_human_merged_build_and_staging_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'workflows: ["Staging deploy"]' in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.event == 'push'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
    assert "Build 230: seed Bennett procurement planning requirements" in workflow
    assert "runner.temp" not in workflow
    assert (
        "/tmp/iron-house-os-bennett-staging-procurement-${{ github.run_id }}-${{ github.run_attempt }}"
        in workflow
    )
    assert 'test "$RELEASE_SHA" = "$(git rev-parse origin/main)"' in workflow
    assert "Live staging release mismatch" in workflow
    assert "bennett_procurement_staging_pilot" in workflow
    assert "--base-url https://staging.os.ironhousecivil.com" in workflow
    assert "http://127.0.0.1:8000" not in workflow
    assert "retention-days: 90" in workflow


def test_approval_marker_and_tool_match_the_exact_authorized_boundary() -> None:
    marker = json.loads(MARKER.read_text(encoding="utf-8"))
    tool = PROCUREMENT_TOOL.read_text(encoding="utf-8")

    assert marker["issue"] == 375
    assert marker["environment"] == "staging"
    assert marker["source_revision"] == "2026-08-27-final"
    assert "Build 230" in marker["trigger"]
    assert marker["exact_records"]["job_number"] == "IH2026002"
    assert marker["original_cost_budget"] == "26660.93"
    assert len(marker["planning_requirements"]) == 4
    assert marker["planning_requirements"][0]["order_quantity"] is None
    assert marker["excluded_allowance"] == {
        "source_code": "RISK",
        "amount": "4750.00",
        "reason": "Subgrade and buried deficiencies are an original-budget allowance, not an authorized procurement requirement.",
    }
    assert "infer or confirm the ready-mix order quantity" in marker["prohibited_actions"]
    assert "book rentals or trucking" in marker["prohibited_actions"]
    assert "mutate production" in marker["prohibited_actions"]

    assert "/api/v1/auth/login" in tool
    assert "/api/v1/finance/projects/{PROJECT_ID}/import-estimate" in tool
    assert '"approval_boundary": "staging_procurement_planning_only_no_commitments"' in tool
    assert "PROCUREMENT_REQUIREMENTS" in tool
    assert "purchase-orders" not in tool
    assert "quickbooks" not in tool
