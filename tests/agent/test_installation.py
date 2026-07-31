from pathlib import Path


def test_start_installation_restarts_already_active_service() -> None:
    installer = Path("ops/agent/install.sh").read_text(encoding="utf-8")
    commands = {line.strip() for line in installer.splitlines()}

    assert "systemctl enable iron-house-agent.service" in commands
    assert "systemctl restart iron-house-agent.service" in commands
    assert "systemctl enable --now iron-house-agent.service" not in commands
