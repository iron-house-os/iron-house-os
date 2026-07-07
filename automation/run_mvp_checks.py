#!/usr/bin/env python3
"""Run fast MVP checks for Iron House OS.

The script is designed for both local runner use and GitHub Actions. It skips a
check if that runtime is not available, so the Build Agent can still create a PR
with useful output on a minimal machine.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures = 0
    failures += _run_if_available("python", ["python", "-m", "compileall", "backend/app"], ROOT)
    failures += _run_if_available("python", ["python", "-m", "pytest"], ROOT / "backend")
    failures += _run_if_available("npm", ["npm", "run", "build"], ROOT / "frontend")
    return 1 if failures else 0


def _run_if_available(binary: str, command: list[str], cwd: Path) -> int:
    if shutil.which(binary) is None:
        print(f"Skipping {' '.join(command)} because {binary} is not installed.")
        return 0
    print(f"Running {' '.join(command)} in {cwd}")
    result = subprocess.run(command, cwd=cwd, check=False)
    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
