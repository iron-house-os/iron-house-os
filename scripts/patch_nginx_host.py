#!/usr/bin/env python3
"""Apply Ubuntu's NGINX security update during an approved production cutover."""

import os
from pathlib import Path
import platform
import subprocess


# Ubuntu USN-9159-1, published 2026-11-19.
FIXED_PACKAGES = {
    "20.04": "1.18.0-0ubuntu1.7+esm5",
    "22.04": "1.18.0-6ubuntu14.23",
    "24.04": "1.24.0-2ubuntu7.20",
    "26.04": "1.28.3-2ubuntu1.13",
    "26.10": "1.30.4-7ubuntu1.2",
}


def output(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def patch_host() -> None:
    if os.geteuid() != 0:
        raise RuntimeError("The approved host update requires root.")
    release = platform.freedesktop_os_release()
    if release.get("ID") != "ubuntu" or release.get("VERSION_ID") not in FIXED_PACKAGES:
        raise RuntimeError("This host requires its distribution-specific NGINX advisory.")
    minimum = FIXED_PACKAGES[release["VERSION_ID"]]
    owner = output("dpkg-query", "-S", "/usr/sbin/nginx").removesuffix(": /usr/sbin/nginx")
    package = owner.split(":")[0]
    if package not in {"nginx", "nginx-core", "nginx-full", "nginx-extras", "nginx-light"}:
        raise RuntimeError("The running NGINX binary must use an Ubuntu NGINX package.")
    installed = output("dpkg-query", "-W", "-f=${Version}", package)
    if "ubuntu" not in installed:
        raise RuntimeError("The NGINX package needs its upstream vendor advisory.")

    # Validate before apt can restart the service through a package maintainer script.
    subprocess.run(["/usr/sbin/nginx", "-t"], check=True)
    comparison = subprocess.run(["dpkg", "--compare-versions", installed, "ge", minimum])
    if comparison.returncode == 1:
        subprocess.run(["apt-get", "update"], check=True)
        packages = sorted({"nginx", "nginx-common", package})
        subprocess.run(
            ["apt-get", "install", "-y", "--only-upgrade", "--no-remove", *packages],
            check=True,
            env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
        )
    elif comparison.returncode != 0:
        comparison.check_returncode()
    installed = output("dpkg-query", "-W", "-f=${Version}", package)
    if "ubuntu" not in installed:
        raise RuntimeError("The updated NGINX package is outside the reviewed Ubuntu source.")
    subprocess.run(["dpkg", "--compare-versions", installed, "ge", minimum], check=True)
    subprocess.run(["/usr/sbin/nginx", "-t"], check=True)
    subprocess.run(["systemctl", "restart", "nginx"], check=True)
    subprocess.run(["systemctl", "is-active", "--quiet", "nginx"], check=True)
    pid = output("systemctl", "show", "nginx", "--property=MainPID", "--value")
    if not pid.isdecimal() or int(pid) <= 0:
        raise RuntimeError("NGINX has no running master process after restart.")
    executable = Path(f"/proc/{pid}/exe")
    if not executable.samefile("/usr/sbin/nginx"):
        raise RuntimeError("The NGINX master is not running the installed patched binary.")
    print(f"Verified Ubuntu {release['VERSION_ID']} {package}={installed}", flush=True)
    subprocess.run(["/usr/sbin/nginx", "-v"], check=True)


if __name__ == "__main__":
    patch_host()
