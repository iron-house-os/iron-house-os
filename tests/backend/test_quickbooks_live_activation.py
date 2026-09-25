import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "ops/digitalocean/quickbooks-live-read-only-wrapper.sh"
WORKFLOW = ROOT / ".github/workflows/quickbooks-live-read-only.yml"
CUTOVER = ROOT / "ops/digitalocean/cutover.sh"
CONFIG_SCRIPT = ROOT / "ops/scripts/quickbooks_live_config.py"
SPEC = importlib.util.spec_from_file_location("quickbooks_live_config", CONFIG_SCRIPT)
CONFIG = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(CONFIG)


def test_live_control_is_manual_protected_and_exact_release_only() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "environment: production" in workflow
    assert "runs-on: [self-hosted, linux, ihos-production]" in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert '[[ "$RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]]' in workflow
    assert '[[ "$(git rev-parse HEAD)" == "$RELEASE_SHA" ]]' in workflow
    assert 'git merge-base --is-ancestor "$RELEASE_SHA" origin/main' in workflow
    assert "/etc/iron-house-os/production.env" not in workflow
    assert "secrets." not in workflow
    assert workflow.count("issues: write") == 1
    configure_job = workflow.split("  configure-production:", 1)[1]
    assert "    permissions:\n      contents: read\n      issues: write" in configure_job


def test_live_wrapper_keeps_credentials_database_managed_and_generates_key_on_host() -> None:
    wrapper = WRAPPER.read_text()
    config_script = CONFIG_SCRIPT.read_text()

    assert "environment_file=/etc/iron-house-os/production.env" in wrapper
    assert 'hostname)" != "iron-house-os-prod-1"' in wrapper
    assert '"QUICKBOOKS_ENABLED": "false"' in config_script
    assert '"QUICKBOOKS_ENVIRONMENT": "production"' in config_script
    assert '"QUICKBOOKS_LIVE_READ_ONLY_APPROVED": "true"' in config_script
    assert '"QUICKBOOKS_CLIENT_ID": ""' in config_script
    assert '"QUICKBOOKS_CLIENT_SECRET": ""' in config_script
    assert "secrets.token_urlsafe(48)" in config_script
    assert "existing_key if already_active else make_token()" in config_script
    assert "QUICKBOOKS_TOKEN_ENCRYPTION_KEY" not in wrapper.split("echo")[-1]
    assert "GET CompanyInfo only" in wrapper


def test_live_wrapper_has_force_disable_rollback_and_bounded_readiness() -> None:
    wrapper = WRAPPER.read_text()

    assert "quickbooks_live_config.py" in wrapper
    assert 'flock --wait 30 9' in wrapper
    assert "/opt/iron-house-os-actions-runner/_work/_temp" in wrapper
    assert "export COMPOSE_PROJECT_NAME=${production_candidates[0]}" in wrapper
    assert 'export IHOS_RELEASE_ID="$release_sha"' in wrapper
    assert '[[ ! -f "$environment_file" || -L "$environment_file" ]]' in wrapper
    assert '"root:root:600"' in wrapper
    assert '"root:root:400"' in wrapper
    assert "Exactly one production Compose project is required" in wrapper
    assert 'install -o root -g root -m 0600 "$previous_file" "$environment_file"' in wrapper
    assert 'install -o ihos-runner -g ihos-runner -m 0640 "$evidence_candidate"' in wrapper
    assert "--force-recreate backend" in wrapper
    assert "for _attempt in $(seq 1 24)" in wrapper
    assert "within 120 seconds" in wrapper


def test_activation_generates_a_new_host_key_and_exact_live_settings() -> None:
    source = """\
QUICKBOOKS_ENABLED=false
QUICKBOOKS_FORCE_DISABLED=false
QUICKBOOKS_ENVIRONMENT=sandbox
QUICKBOOKS_LIVE_READ_ONLY_APPROVED=false
QUICKBOOKS_CLIENT_ID=
QUICKBOOKS_CLIENT_SECRET=
QUICKBOOKS_TOKEN_ENCRYPTION_KEY=sandbox-key-that-must-not-be-reused
"""

    rendered = CONFIG.render_environment(
        source, "activate", token_factory=lambda: "new-production-key-of-at-least-32-characters"
    )

    assert "QUICKBOOKS_ENABLED=false" in rendered
    assert "QUICKBOOKS_FORCE_DISABLED=false" in rendered
    assert "QUICKBOOKS_ENVIRONMENT=production" in rendered
    assert "QUICKBOOKS_LIVE_READ_ONLY_APPROVED=true" in rendered
    assert "QUICKBOOKS_CLIENT_ID=\n" in rendered
    assert "QUICKBOOKS_CLIENT_SECRET=\n" in rendered
    assert "QUICKBOOKS_TOKEN_ENCRYPTION_KEY=new-production-key-of-at-least-32-characters" in rendered
    assert "sandbox-key-that-must-not-be-reused" not in rendered
    assert f"QUICKBOOKS_REDIRECT_URI={CONFIG.PRODUCTION_REDIRECT_URI}" in rendered
    assert f"QUICKBOOKS_FRONTEND_RETURN_URL={CONFIG.PRODUCTION_RETURN_URI}" in rendered


def test_repeated_activation_preserves_the_existing_production_key() -> None:
    existing_key = "existing-production-key-of-at-least-32-characters"
    source = f"""\
QUICKBOOKS_ENABLED=false
QUICKBOOKS_ENVIRONMENT=production
QUICKBOOKS_LIVE_READ_ONLY_APPROVED=true
QUICKBOOKS_CLIENT_ID=
QUICKBOOKS_CLIENT_SECRET=
QUICKBOOKS_TOKEN_ENCRYPTION_KEY={existing_key}
"""

    rendered = CONFIG.render_environment(
        source,
        "activate",
        token_factory=lambda: pytest.fail("idempotent activation rotated the key"),
    )

    assert f"QUICKBOOKS_TOKEN_ENCRYPTION_KEY={existing_key}" in rendered


def test_activation_rejects_environment_credentials_and_global_enable() -> None:
    with pytest.raises(ValueError, match="database-managed"):
        CONFIG.render_environment("QUICKBOOKS_ENABLED=true\n", "activate")

    with pytest.raises(ValueError, match="administrator UI"):
        CONFIG.render_environment(
            "QUICKBOOKS_ENABLED=false\nQUICKBOOKS_CLIENT_SECRET=do-not-accept\n",
            "activate",
        )


def test_force_disable_changes_only_the_feature_and_kill_switch() -> None:
    source = """\
QUICKBOOKS_ENABLED=false
QUICKBOOKS_FORCE_DISABLED=false
QUICKBOOKS_ENVIRONMENT=production
QUICKBOOKS_LIVE_READ_ONLY_APPROVED=true
QUICKBOOKS_TOKEN_ENCRYPTION_KEY=preserve-this-protected-value
UNRELATED_SETTING=preserve-this-too
"""

    rendered = CONFIG.render_environment(source, "force-disable")

    assert "QUICKBOOKS_ENABLED=false" in rendered
    assert "QUICKBOOKS_FORCE_DISABLED=true" in rendered
    assert "QUICKBOOKS_ENVIRONMENT=production" in rendered
    assert "QUICKBOOKS_LIVE_READ_ONLY_APPROVED=true" in rendered
    assert "QUICKBOOKS_TOKEN_ENCRYPTION_KEY=preserve-this-protected-value" in rendered
    assert "UNRELATED_SETTING=preserve-this-too" in rendered


def test_cutover_installs_restricted_live_control_wrapper() -> None:
    cutover = CUTOVER.read_text()

    assert "install_quickbooks_live_read_only_wrapper" in cutover
    assert "wrapper_target=/usr/local/sbin/ihos-quickbooks-live-read-only" in cutover
    assert "sudoers_target=/etc/sudoers.d/iron-house-os-quickbooks-live-read-only" in cutover
    assert 'install -o root -g root -m 0755 "$wrapper_source" "$wrapper_target"' in cutover
