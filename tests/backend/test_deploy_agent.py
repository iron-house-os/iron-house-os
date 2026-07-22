from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


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
