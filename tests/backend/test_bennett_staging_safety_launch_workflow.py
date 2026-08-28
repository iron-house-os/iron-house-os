import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/bennett-staging-safety-launch.yml"
MARKER = ROOT / "ops/staging-pilots/2026-08-28-bennett-safety-launch.json"
TOOL = ROOT / "backend/app/tools/bennett_safety_launch_staging_pilot.py"


def test_workflow_runs_only_after_exact_human_merged_build_and_staging_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'workflows: ["Staging deploy"]' in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.event == 'push'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
    assert "Build 231: initialize blocked Bennett safety and portal launch controls" in workflow
    assert "runner.temp" not in workflow
    assert (
        "/tmp/iron-house-os-bennett-staging-safety-launch-${{ github.run_id }}-${{ github.run_attempt }}"
        in workflow
    )
    assert 'test "$RELEASE_SHA" = "$(git rev-parse origin/main)"' in workflow
    assert "Live staging release mismatch" in workflow
    assert "bennett_safety_launch_staging_pilot" in workflow
    assert "--base-url https://staging.os.ironhousecivil.com" in workflow
    assert "http://127.0.0.1:8000" not in workflow
    assert "retention-days: 90" in workflow


def test_approval_marker_and_tool_match_the_exact_blocked_boundary() -> None:
    marker = json.loads(MARKER.read_text(encoding="utf-8"))
    tool = TOOL.read_text(encoding="utf-8")

    assert marker["issue"] == 377
    assert marker["environment"] == "staging"
    assert "Build 231" in marker["trigger"]
    assert marker["exact_records"]["job_number"] == "IH2026002"
    assert marker["internal_folder_suffix"] == "13_Award_Handoff/Safety"
    assert len(marker["safety_record_requirements"]) == 6
    assert marker["initial_state"] == {
        "safety_release_status": "blocked",
        "requirement_applicability": "unconfirmed",
        "requirement_status": "not_started",
        "actual_safety_record_count": 0,
        "portal_access_status": "not_started",
        "portal_assignment_count": 0,
        "automatic_portal_provisioning": False,
        "mobilization_status": "not_ready",
        "completed_start_controls": 0,
    }
    assert "create safety evidence" in marker["prohibited_actions"][1]
    assert "assign, invite, activate, or create a portal user" in marker["prohibited_actions"][2]
    assert "mutate production" in marker["prohibited_actions"]

    assert "/api/v1/auth/login" in tool
    assert "/api/v1/projects/{PROJECT_ID}/safety-launch" in tool
    assert '"approval_boundary": "staging_safety_shell_only_no_release_or_access"' in tool
    assert "UserAccount" in tool
    assert "ProjectStartChecklistItem" in tool
    assert "/api/v1/field-operations/employees" not in tool
