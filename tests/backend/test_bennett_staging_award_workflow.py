import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/bennett-staging-award.yml"
MARKER = ROOT / "ops/staging-pilots/2026-08-28-bennett-award-transition.json"
AWARD_TOOL = ROOT / "backend/app/tools/bennett_quote_staging_award.py"


def test_workflow_runs_only_after_exact_human_merged_build_and_staging_deploy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'workflows: ["Staging deploy"]' in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "github.event.workflow_run.event == 'push'" in workflow
    assert "github.event.workflow_run.head_branch == 'main'" in workflow
    assert "Build 228: execute approved Bennett staging award transition" in workflow
    assert "runner.temp" not in workflow
    assert (
        "/tmp/iron-house-os-bennett-staging-award-${{ github.run_id }}-${{ github.run_attempt }}"
        in workflow
    )
    assert 'test "$RELEASE_SHA" = "$(git rev-parse origin/main)"' in workflow
    assert "Live staging release mismatch" in workflow
    assert "bennett_quote_staging_award" in workflow
    assert "--base-url https://staging.os.ironhousecivil.com" in workflow
    assert "http://127.0.0.1:8000" not in workflow
    assert "retention-days: 90" in workflow


def test_approval_marker_and_tool_match_the_exact_authorized_boundary() -> None:
    marker = json.loads(MARKER.read_text(encoding="utf-8"))
    tool = AWARD_TOOL.read_text(encoding="utf-8")

    assert marker["issue"] == 371
    assert marker["environment"] == "staging"
    assert marker["source_revision"] == "2026-08-27-final"
    assert "replied Accepted" in marker["approval_evidence"]
    assert "Build 228" in marker["trigger"]
    assert marker["exact_records"] == {
        "project_id": "9ece69c0-cd6b-4d7b-b208-df77ed849e23",
        "workspace_id": "6f3a07a7-6c9b-48bc-9711-0ae8230bc7b2",
        "quote_id": "8f854940-e710-45c2-aae4-7d5706c3a9e2",
        "quote_number": "Q-2026-002",
    }
    assert marker["expected_quote"] == {
        "subtotal": "36266.67",
        "gst": "1813.33",
        "total": "38080.00",
    }
    assert "mutate production" in marker["prohibited_actions"]
    assert "issue or externally send the quote" in marker["prohibited_actions"]

    assert "/api/v1/auth/login" in tool
    assert '/api/v1/customer-quotes/{QUOTE_ID}/accept' in tool
    assert '"approval_boundary": "staging_acceptance_award_no_external_issue"' in tool
    assert "JOB_NUMBER_PATTERN" in tool
    assert "/issue-status" not in tool
