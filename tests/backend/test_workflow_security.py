from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.check_workflow_security import (  # noqa: E402
    APPROVED_REMOTE_ACTIONS,
    inspect_workflows,
)


def write_workflow(root: Path, content: str) -> None:
    workflow_root = root / ".github" / "workflows"
    workflow_root.mkdir(parents=True)
    (workflow_root / "test.yml").write_text(content, encoding="utf-8")


def valid_workflow(action: str = "actions/checkout") -> str:
    approved = APPROVED_REMOTE_ACTIONS[action]
    return f"""name: Test
on: workflow_dispatch
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: {action}@{approved['sha']} # {approved['version']}
"""


def test_current_workflows_use_immutable_approved_actions_and_explicit_permissions() -> None:
    result = inspect_workflows(ROOT)

    assert result["status"] == "passed", result["errors"]
    assert result["workflow_files"] > 0
    assert result["action_references"] > 0


def test_mutable_major_action_tag_fails_closed(tmp_path: Path) -> None:
    write_workflow(
        tmp_path,
        valid_workflow().replace(
            f"actions/checkout@{APPROVED_REMOTE_ACTIONS['actions/checkout']['sha']}",
            "actions/checkout@v4",
        ),
    )

    result = inspect_workflows(tmp_path)

    assert result["status"] == "failed"
    assert any("full 40-character commit SHA" in error for error in result["errors"])


def test_missing_top_level_permissions_fails_closed(tmp_path: Path) -> None:
    write_workflow(tmp_path, valid_workflow().replace("permissions:\n  contents: read\n", ""))

    result = inspect_workflows(tmp_path)

    assert result["status"] == "failed"
    assert any("missing explicit top-level permissions" in error for error in result["errors"])


def test_unapproved_remote_action_fails_closed(tmp_path: Path) -> None:
    write_workflow(
        tmp_path,
        valid_workflow().replace(
            "actions/checkout@",
            "third-party/example@",
        ),
    )

    result = inspect_workflows(tmp_path)

    assert result["status"] == "failed"
    assert any("not in the approved allowlist" in error for error in result["errors"])


def test_unapproved_local_action_path_fails_closed(tmp_path: Path) -> None:
    write_workflow(
        tmp_path,
        valid_workflow().replace(
            f"actions/checkout@{APPROVED_REMOTE_ACTIONS['actions/checkout']['sha']} # v4",
            "./scripts/build-action",
        ),
    )

    result = inspect_workflows(tmp_path)

    assert result["status"] == "failed"
    assert any("must be under ./.github/actions/" in error for error in result["errors"])
