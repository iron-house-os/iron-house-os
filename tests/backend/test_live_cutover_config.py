import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_approved_host_plan_is_fail_closed_and_within_budget() -> None:
    plan = json.loads((ROOT / "ops/digitalocean/host-plan.json").read_text())

    assert plan["approval"]["authorization"] == "Approve Build 216"
    assert plan["approval"]["approved_by_email"] == "jeremie@ironhousecontracting.com"
    assert plan["host"]["provider"] == "DigitalOcean"
    assert plan["host"]["region"] == "tor1"
    assert plan["budget"] == {
        "currency": "CAD",
        "monthly_cap": 60.0,
        "automatic_upgrade_allowed": False,
    }
    assert plan["network"]["domain"] == "os.ironhousecivil.com"
    assert plan["network"]["application_bind"] == "127.0.0.1:8080"
    assert plan["storage"]["region"] == "ca-central-1"
    assert plan["storage"]["public_access"] is False
    assert plan["storage"]["versioning_required"] is True
    assert plan["storage"]["encryption_required"] is True
    assert plan["cutover"]["decision"] == "PENDING"
    assert plan["cutover"]["release_sha"] is None
    assert plan["cutover"]["operator_email"] == "jeremie@ironhousecontracting.com"
    assert plan["cutover"]["approver_email"] == "jeremie@ironhousecontracting.com"


def test_production_compose_does_not_expose_application_port_publicly() -> None:
    compose = (ROOT / "docker-compose.production.yml").read_text()

    assert '- "127.0.0.1:${IHOS_PORT:-8080}:80"' in compose
    assert '- "${IHOS_PORT:-8080}:80"' not in compose


def test_gateway_configs_hold_maintenance_until_live_gate() -> None:
    maintenance = (ROOT / "ops/digitalocean/nginx-maintenance.conf").read_text()
    live = (ROOT / "ops/digitalocean/nginx-live.conf").read_text()
    cutover = (ROOT / "ops/digitalocean/cutover.sh").read_text()

    assert 'return 503 "Iron House OS maintenance in progress.\\n";' in maintenance
    assert "proxy_pass http://127.0.0.1:8080;" not in maintenance
    assert "ssl_certificate /etc/letsencrypt/live/os.ironhousecivil.com/fullchain.pem;" in live
    assert "proxy_pass http://127.0.0.1:8080;" in live
    assert "--confirm-go" in cutover
    assert "--evidence" in cutover
    assert "verify_release_candidate_evidence.py" in cutover
    assert "rollback_maintenance" in cutover
    assert "scripts/verify_s3_targets.sh" in cutover
    assert "pre-cutover-$stamp" in cutover
    assert "post-cutover-$stamp" in cutover


def test_cloud_init_contains_no_production_credentials() -> None:
    cloud_init = (ROOT / "ops/digitalocean/cloud-init.yaml").read_text()

    assert "AWS_ACCESS_KEY_ID=" not in cloud_init
    assert "AWS_SECRET_ACCESS_KEY=" not in cloud_init
    assert "BOOTSTRAP_ADMIN_PASSWORD=" not in cloud_init
    assert "ssh_pwauth: false" in cloud_init
    assert "ufw, --force, enable" in cloud_init


def test_release_smoke_uses_the_real_project_scoped_drawing_route() -> None:
    smoke = (ROOT / "scripts/release_smoke.py").read_text()

    assert "/api/v1/drawing-intelligence/projects/{project_id}" in smoke
    assert "/api/v1/drawing-intelligence/project/{project_id}" not in smoke
