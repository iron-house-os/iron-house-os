from pathlib import Path

import pytest

from ops.agent.iron_house_agent.apparmor import prepare_bwrap_profile

STOCK_NOBLE_PROFILE = """\
profile bwrap /usr/bin/bwrap flags=(attach_disconnected) {
  allow userns,
}
profile unpriv_bwrap flags=(attach_disconnected) {
  allow userns,
}
"""


def test_prepare_bwrap_profile_adds_deleted_dentry_mediation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    first = tmp_path / "first"
    second = tmp_path / "second"
    source.write_text(STOCK_NOBLE_PROFILE, encoding="utf-8")

    prepare_bwrap_profile(source, first)
    prepare_bwrap_profile(first, second)

    prepared = first.read_text(encoding="utf-8")
    assert prepared.count("mediate_deleted") == 2
    assert second.read_text(encoding="utf-8") == prepared


def test_prepare_bwrap_profile_rejects_unexpected_package_profile(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("profile something_else flags=(attach_disconnected) {}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="bwrap"):
        prepare_bwrap_profile(source, destination)

    assert not destination.exists()
