from pathlib import Path


def test_backend_tests_live_in_collected_tree() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    uncollected_tests = sorted(
        path.relative_to(repository_root).as_posix()
        for path in (repository_root / "backend" / "tests").glob("test_*.py")
    )

    assert not uncollected_tests, (
        "Backend test files must live under tests/backend so CI collects them: "
        + ", ".join(uncollected_tests)
    )
