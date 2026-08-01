from __future__ import annotations

import argparse
import re
from pathlib import Path

_PROFILE_NAMES = ("bwrap", "unpriv_bwrap")


def prepare_bwrap_profile(source: Path, destination: Path) -> None:
    profile = source.read_text(encoding="utf-8")
    for name in _PROFILE_NAMES:
        pattern = re.compile(
            rf"^(profile\s+{re.escape(name)}(?:\s+/usr/bin/bwrap)?\s+flags=\()([^)]*)(\)\s*\{{)",
            re.MULTILINE,
        )
        match = pattern.search(profile)
        if match is None:
            raise ValueError(f"Required AppArmor profile declaration is missing: {name}")
        flags = [flag.strip() for flag in match.group(2).split(",") if flag.strip()]
        if "mediate_deleted" not in flags:
            flags.append("mediate_deleted")
            replacement = f"{match.group(1)}{','.join(flags)}{match.group(3)}"
            profile = profile[: match.start()] + replacement + profile[match.end() :]
    destination.write_text(profile, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare Ubuntu's Bubblewrap AppArmor profile for reliable Codex workloads"
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    prepare_bwrap_profile(arguments.source, arguments.destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
