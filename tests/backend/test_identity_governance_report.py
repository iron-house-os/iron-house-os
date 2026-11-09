from app.tools.identity_governance_report import evidence_envelope, exit_code_for_findings


def test_evidence_envelope_is_repeatably_hashed_and_secret_safe() -> None:
    payload = {
        "summary": {"total_accounts": 1},
        "findings": [{"severity": "high", "code": "single_active_administrator"}],
        "accounts": [{"email": "jeremie@ironhousecontracting.com"}],
    }
    first = evidence_envelope(payload)
    second = evidence_envelope(payload)

    assert first["schema_version"] == 1
    assert first["snapshot_sha256"] == second["snapshot_sha256"]
    assert len(first["snapshot_sha256"]) == 64
    assert first["snapshot"] == payload
    assert "password" not in str(first).lower()


def test_alert_exit_code_obeys_configured_threshold() -> None:
    findings = [{"severity": "normal"}, {"severity": "high"}]
    assert exit_code_for_findings(findings, "never") == 0
    assert exit_code_for_findings(findings, "critical") == 0
    assert exit_code_for_findings(findings, "high") == 3
    assert exit_code_for_findings(findings, "normal") == 3
