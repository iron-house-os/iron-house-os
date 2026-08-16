import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECKOUT_PIN = "11d5960a326750d5838078e36cf38b85af677262"


def test_deploy_agent_requires_both_release_gates_and_allowlisted_cutover() -> None:
    script = (ROOT / "ops/deploy-agent/deploy.sh").read_text(encoding="utf-8")

    assert 'gate "CI"' in script
    assert 'gate "Release readiness"' in script
    assert "bash ops/digitalocean/cutover.sh" in script
    assert "--confirm-go" in script
    assert "eval " not in script


def test_deploy_agent_timer_is_bounded_and_persistent() -> None:
    timer = (ROOT / "ops/systemd/ihos-deploy-agent.timer").read_text(encoding="utf-8")
    service = (ROOT / "ops/systemd/ihos-deploy-agent.service").read_text(encoding="utf-8")

    assert "OnUnitActiveSec=2min" in timer
    assert "Persistent=true" in timer
    assert "TimeoutStartSec=45min" in service
    assert "ExecStart=/bin/bash" in service


def test_production_cutover_handoff_is_permission_safe() -> None:
    wrapper = (ROOT / "ops/digitalocean/production-deploy-wrapper.sh").read_text(
        encoding="utf-8"
    )
    cutover = ROOT / "ops/digitalocean/cutover.sh"

    assert 'exec /bin/bash "$release_root/ops/digitalocean/cutover.sh"' in wrapper
    assert cutover.stat().st_mode & stat.S_IXUSR


def test_production_deploy_uses_trusted_workflow_tooling() -> None:
    workflow = (ROOT / ".github/workflows/production-deploy.yml").read_text(
        encoding="utf-8"
    )

    assert "if: github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main'" in workflow
    assert "name: Checkout trusted deploy tooling at workflow commit" in workflow
    assert "name: Checkout approved release SHA" in workflow
    assert workflow.count(f"uses: actions/checkout@{CHECKOUT_PIN}") == 3
    assert "ref: ${{ github.workflow_sha }}" in workflow
    assert "path: .deploy-tooling" in workflow
    assert workflow.count("persist-credentials: false") == 2
    assert 'cmp --silent "$trusted_wrapper" "$installed_wrapper"' in workflow
    assert '"root:root:755"' in workflow
    assert "sudo -n /usr/local/sbin/ihos-production-deploy" in workflow
    assert "sudo /bin/bash" not in workflow


def test_production_runner_has_bounded_wrapper_refresh_mode() -> None:
    installer = (ROOT / "ops/digitalocean/install-production-runner.sh").read_text(
        encoding="utf-8"
    )

    assert "--refresh-wrapper-only" in installer
    assert 'if [[ "$mode" == "refresh-wrapper" ]]' in installer
    assert installer.index('install -o root -g root -m 0755') < installer.index(
        'if [[ "$mode" == "refresh-wrapper" ]]'
    )
    assert installer.index('if [[ "$mode" == "refresh-wrapper" ]]') < installer.index(
        "gh auth status"
    )
