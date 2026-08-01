from pathlib import Path


def test_start_installation_restarts_already_active_service() -> None:
    installer = Path("ops/agent/install.sh").read_text(encoding="utf-8")
    commands = {line.strip() for line in installer.splitlines()}

    assert "systemctl enable iron-house-agent.service" in commands
    assert "systemctl restart iron-house-agent.service" in commands
    assert "systemctl enable --now iron-house-agent.service" not in commands
    assert 'sudo -u "${AGENT_USER}" -H gh auth setup-git' in commands


def test_service_allows_codex_sandbox_without_removing_filesystem_hardening() -> None:
    unit = Path("ops/agent/iron-house-agent.service").read_text(encoding="utf-8")

    assert "User=ih-agent" in unit
    assert "NoNewPrivileges=false" in unit
    assert "ProtectSystem=strict" in unit
    assert "PrivateTmp=true" in unit
    assert "ReadWritePaths=/srv/iron-house-agents /var/lib/iron-house-agent" in unit
