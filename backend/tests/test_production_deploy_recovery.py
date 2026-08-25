from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_production_wrapper_recovers_one_stopped_compose_project() -> None:
    wrapper = (
        REPOSITORY_ROOT / "ops" / "digitalocean" / "production-deploy-wrapper.sh"
    ).read_text(encoding="utf-8")

    assert "docker_ps+=(--all)" in wrapper
    assert "sort -u" in wrapper
    assert '"${#production_candidates[@]}" != 1' in wrapper
    assert "Exactly one production Compose project is required" in wrapper


def test_cutover_polls_exact_release_readiness_after_start() -> None:
    cutover = (
        REPOSITORY_ROOT / "ops" / "digitalocean" / "cutover.sh"
    ).read_text(encoding="utf-8")

    assert '"${compose[@]}" up -d --no-build' in cutover
    assert "for attempt in $(seq 1 24)" in cutover
    assert 'expected = os.environ["IHOS_RELEASE_ID"]' in cutover
    assert "within 120 seconds" in cutover
    assert '"${compose[@]}" up -d --no-build --wait' not in cutover
