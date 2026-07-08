from app.services.system_readiness import get_system_readiness


def test_system_readiness_reports_enabled_mvp_services():
    readiness = get_system_readiness()

    assert readiness["status"] == "ready"
    assert readiness["checks"]["takeoff_engine"] == "enabled"
    assert readiness["checks"]["estimate_workspace"] == "enabled"
    assert readiness["checks"]["rfq_linkage"] == "enabled"
    assert readiness["checks"]["project_readiness"] == "enabled"
