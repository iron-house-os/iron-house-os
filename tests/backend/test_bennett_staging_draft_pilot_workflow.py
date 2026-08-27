import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/bennett-staging-draft-pilot.yml"
MARKER = ROOT / "ops/staging-pilots/2026-08-27-bennett-draft-pilot.json"
PILOT_TOOL = ROOT / "backend/app/tools/bennett_estimate_quote_staging_pilot.py"


def test_workflow_runs_only_after_exact_human_merged_build_and_staging_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'workflows: ["Staging deploy"]' in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.event == 'push'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
    assert "Build 225: repair Bennett staging pilot prerequisites and prove draft handoff" in workflow
    assert 'test "$RELEASE_SHA" = "$(git rev-parse origin/main)"' in workflow
    assert "Live staging release mismatch" in workflow
    assert "bennett_strata_staging_import" in workflow
    assert "bennett_estimate_quote_staging_pilot" in workflow
    assert "retention-days: 90" in workflow


def test_approval_marker_and_pilot_are_draft_only() -> None:
    marker = json.loads(MARKER.read_text(encoding="utf-8"))
    tool = PILOT_TOOL.read_text(encoding="utf-8")

    assert marker["environment"] == "staging"
    assert marker["source_revision"] == "2026-08-27-final"
    assert marker["expected_concrete_quote"] == {
        "subtotal": "36266.67",
        "gst": "1813.33",
        "total": "38080.00",
    }
    assert marker["options"]["selected_option_id"] is None
    assert marker["options"]["draft_selected_options_total"] == "0.00"
    assert "accept quote" in marker["prohibited_actions"]
    assert "award project" in marker["prohibited_actions"]
    assert "mutate production" in marker["prohibited_actions"]

    assert "/api/v1/auth/login" in tool
    assert "/api/v1/customer-quotes/from-estimate/" in tool
    assert '"approval_boundary": "draft_only_no_award"' in tool
    assert "/accept" not in tool
    assert "/issue-status" not in tool
