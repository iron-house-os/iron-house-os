#!/usr/bin/env python3
"""Repository wrapper for the packaged administrator recovery operator tool."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.tools.admin_access_recovery import main  # noqa: E402


if __name__ == "__main__":
    main()
