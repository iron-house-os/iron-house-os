from pathlib import Path


def test_start_installation_restarts_already_active_service() -> None:
    installer = Path("ops/agent/install.sh").read_text(encoding="utf-8")
    commands = {line.strip() for line in installer.splitlines()}

    assert "systemctl enable iron-house-agent.service" in commands
    assert "systemctl restart iron-house-agent.service" in commands
    assert "systemctl enable --now iron-house-agent.service" not in commands
    assert 'sudo -u "${AGENT_USER}" -H gh auth setup-git' in commands


def test_installer_configures_ubuntu_2404_bubblewrap_apparmor_profile() -> None:
    installer = Path("ops/agent/install.sh").read_text(encoding="utf-8")

    assert "bubblewrap" in installer
    assert "apparmor-profiles" in installer
    assert "apparmor-utils" in installer
    assert "/usr/share/apparmor/extra-profiles/bwrap-userns-restrict" in installer
    assert 'apparmor_parser -r "${installed_profile}"' in installer
    assert 'rm -f "${disabled_profile}"' in installer
    assert "kernel.apparmor_restrict_unprivileged_userns=0" not in installer


def test_start_activation_stops_old_worker_before_repair_and_preflight() -> None:
    installer = Path("ops/agent/install.sh").read_text(encoding="utf-8")

    stop = installer.index("systemctl stop iron-house-agent.service")
    sandbox_setup = installer.index("install_codex_sandbox_prerequisites", stop)
    preflight = installer.index("/usr/local/bin/iron-house-agent preflight", sandbox_setup)
    restart = installer.index("systemctl restart iron-house-agent.service", preflight)

    assert stop < sandbox_setup < preflight < restart


def test_service_allows_codex_sandbox_without_removing_filesystem_hardening() -> None:
    unit = Path("ops/agent/iron-house-agent.service").read_text(encoding="utf-8")

    assert "User=ih-agent" in unit
    assert "NoNewPrivileges=false" in unit
    assert "ProtectSystem=strict" in unit
    assert "PrivateTmp=true" in unit
    assert "ReadWritePaths=/srv/iron-house-agents /var/lib/iron-house-agent" in unit
