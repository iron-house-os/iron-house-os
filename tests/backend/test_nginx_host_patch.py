import importlib.util
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("patch_nginx_host", ROOT / "scripts/patch_nginx_host.py")
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)


@pytest.fixture
def host(monkeypatch):
    state = {"version": "1.24.0-2ubuntu7.19", "updates": True, "commands": []}
    monkeypatch.setattr(patcher.os, "geteuid", lambda: 0)
    monkeypatch.setattr(patcher.platform, "freedesktop_os_release", lambda: {"ID": "ubuntu", "VERSION_ID": "24.04"})
    monkeypatch.setattr(patcher.Path, "samefile", lambda *_: True)

    def output(*args):
        if args[:2] == ("dpkg-query", "-S"):
            return "nginx: /usr/sbin/nginx"
        if args[0] == "systemctl":
            return "1234"
        return state["version"]

    def run(args, check=False, **kwargs):
        state["commands"].append(args)
        result = 0
        if args[:2] == ["apt-get", "install"] and state["updates"]:
            state["version"] = "1.24.0-2ubuntu7.20"
        if args[0] == "dpkg":
            result = int(args[2] < args[4])
        completed = subprocess.CompletedProcess(args, result)
        if check:
            completed.check_returncode()
        return completed

    monkeypatch.setattr(patcher, "output", output)
    monkeypatch.setattr(patcher.subprocess, "run", run)
    return state


def test_updates_old_host_and_restarts_verified_binary(host):
    patcher.patch_host()
    commands = host["commands"]
    assert ["apt-get", "install", "-y", "--only-upgrade", "--no-remove", "nginx", "nginx-common"] in commands
    assert commands.index(["/usr/sbin/nginx", "-t"]) < commands.index(["apt-get", "update"])
    assert ["systemctl", "restart", "nginx"] in commands
    assert ["systemctl", "is-active", "--quiet", "nginx"] in commands


def test_already_patched_host_skips_package_changes(host):
    host["version"] = "1.24.0-2ubuntu7.20"
    patcher.patch_host()
    assert not any(command[0] == "apt-get" for command in host["commands"])


def test_missing_distribution_fix_stops_before_restart(host):
    host["updates"] = False
    with pytest.raises(subprocess.CalledProcessError):
        patcher.patch_host()
    assert ["systemctl", "restart", "nginx"] not in host["commands"]


def test_wrong_running_binary_fails_verification(host, monkeypatch):
    monkeypatch.setattr(patcher.Path, "samefile", lambda *_: False)
    with pytest.raises(RuntimeError, match="patched binary"):
        patcher.patch_host()


@pytest.mark.parametrize("release", [{"ID": "debian", "VERSION_ID": "12"}, {"ID": "ubuntu", "VERSION_ID": "18.04"}])
def test_unknown_distribution_does_not_modify_host(host, monkeypatch, release):
    monkeypatch.setattr(patcher.platform, "freedesktop_os_release", lambda: release)
    with pytest.raises(RuntimeError, match="distribution-specific"):
        patcher.patch_host()
    assert host["commands"] == []


def test_upstream_package_requires_vendor_advisory(host):
    host["version"] = "1.30.6-1~noble"
    with pytest.raises(RuntimeError, match="vendor advisory"):
        patcher.patch_host()
    assert host["commands"] == []


def test_unprivileged_execution_does_not_modify_host(host, monkeypatch):
    monkeypatch.setattr(patcher.os, "geteuid", lambda: 1000)
    with pytest.raises(RuntimeError, match="root"):
        patcher.patch_host()
    assert host["commands"] == []


def test_dispatch_is_bound_to_merged_repair_and_existing_workflow():
    workflow = (ROOT / ".github/workflows/nginx-security-repair.yml").read_text()
    assert 'repos/${GITHUB_REPOSITORY}/pulls/431' in workflow
    assert '.merge_commit_sha' in workflow
    assert 'github.event.workflow_run.event == \'push\'' in workflow
    assert 'head_repository.full_name == github.repository' in workflow
    assert 'gh workflow run production-deploy.yml' in workflow
    assert 'sudo' not in workflow
    production = (ROOT / ".github/workflows/production-deploy.yml").read_text()
    assert 'environment: production' in production
