import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/bennett-staging-cost-budget.yml"
MARKER = ROOT / "ops/staging-pilots/2026-08-28-bennett-cost-budget.json"
BUDGET_TOOL = ROOT / "backend/app/tools/bennett_cost_budget_staging_pilot.py"


def test_workflow_runs_only_after_exact_human_merged_build_and_staging_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'workflows: ["Staging deploy"]' in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.event == 'push'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
    assert "Build 229: seed awarded Bennett cost budget and job codes" in workflow
    assert "runner.temp" not in workflow
    assert (
        "/tmp/iron-house-os-bennett-staging-cost-budget-${{ github.run_id }}-${{ github.run_attempt }}"
        in workflow
    )
    assert 'test "$RELEASE_SHA" = "$(git rev-parse origin/main)"' in workflow
    assert "Live staging release mismatch" in workflow
    assert "bennett_cost_budget_staging_pilot" in workflow
    assert "--base-url https://staging.os.ironhousecivil.com" in workflow
    assert "http://127.0.0.1:8000" not in workflow
    assert "retention-days: 90" in workflow


def test_approval_marker_and_tool_match_the_exact_authorized_boundary() -> None:
    marker = json.loads(MARKER.read_text(encoding="utf-8"))
    tool = BUDGET_TOOL.read_text(encoding="utf-8")

    assert marker["issue"] == 373
    assert marker["environment"] == "staging"
    assert marker["source_revision"] == "2026-08-27-final"
    assert "Build 229" in marker["trigger"]
    assert marker["exact_records"] == {
        "project_id": "9ece69c0-cd6b-4d7b-b208-df77ed849e23",
        "job_number": "IH2026002",
        "workspace_id": "6f3a07a7-6c9b-48bc-9711-0ae8230bc7b2",
        "quote_id": "8f854940-e710-45c2-aae4-7d5706c3a9e2",
        "quote_number": "Q-2026-002",
    }
    assert marker["original_cost_budget"]["total"] == "26660.93"
    assert len(marker["original_cost_budget"]["allocations"]) == 5
    assert "create a commitment, actual cost, purchase order, invoice, or accounting export" in marker["prohibited_actions"]
    assert "issue or externally send the quote" in marker["prohibited_actions"]
    assert "mutate production" in marker["prohibited_actions"]

    assert "/api/v1/auth/login" in tool
    assert "/api/v1/finance/projects/{PROJECT_ID}/import-estimate" in tool
    assert '"approval_boundary": "staging_original_budget_only_no_commitments"' in tool
    assert 'JOB_NUMBER = "IH2026002"' in tool
    assert "purchase-orders" not in tool
    assert "quickbooks" not in tool
