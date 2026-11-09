import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/bennett-staging-production-gate.yml"
MARKER = ROOT / "ops/staging-pilots/2026-08-28-bennett-production-gate.json"
TOOL = ROOT / "backend/app/tools/bennett_production_gate_staging_pilot.py"


def test_workflow_runs_only_after_exact_human_merged_build_and_staging_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'workflows: ["Staging deploy"]' in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.event == 'push'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
    assert "Build 232: control Bennett field production posting" in workflow
    assert "runner.temp" not in workflow
    assert (
        "/tmp/iron-house-os-bennett-staging-production-gate-${{ github.run_id }}-${{ github.run_attempt }}"
        in workflow
    )
    assert 'test "$RELEASE_SHA" = "$(git rev-parse origin/main)"' in workflow
    assert "Live staging release mismatch" in workflow
    assert "bennett_production_gate_staging_pilot" in workflow
    assert "--base-url https://staging.os.ironhousecivil.com" in workflow
    assert "http://127.0.0.1:8000" not in workflow
    assert "retention-days: 90" in workflow


def test_approval_marker_and_tool_match_the_read_only_zero_state_boundary() -> None:
    marker = json.loads(MARKER.read_text(encoding="utf-8"))
    tool = TOOL.read_text(encoding="utf-8")

    assert marker["issue"] == 379
    assert marker["environment"] == "staging"
    assert "Build 232" in marker["trigger"]
    assert marker["exact_records"]["job_number"] == "IH2026002"
    assert marker["required_state"]["production_posting_status"] == "blocked"
    assert marker["required_state"]["daily_sheet_count"] == 0
    assert marker["required_state"]["production_post_count"] == 0
    assert marker["required_state"]["field_photo_count"] == 0
    assert marker["required_state"]["ticket_evidence_count"] == 0
    assert "fabricate Day 1 or Day 2 field facts" in marker["prohibited_actions"]
    assert "mutate production" in marker["prohibited_actions"]

    assert "/api/v1/auth/login" in tool
    assert "/api/v1/daily-timesheets/bootstrap" in tool
    assert 'APPROVAL_BOUNDARY = "staging_production_gate_only_no_field_records"' in tool
    assert 'method="POST"' not in tool.replace(
        'method="POST",\n        body={"email": email, "password": password},', ""
    ).replace('method="POST", expected_status=204', "")
    assert "/post" not in tool
