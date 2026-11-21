import pytest

from app.services.drawing_takeoff_math import (
    TrenchSegment,
    calculate_run,
    calculate_segment,
    owner_crew_pipe_days,
)


def segment(**changes):
    kwargs = dict(
        sheet_revision="C",
        drawing_reference="C-101 sta 0+000 to 0+045",
        station_from_m=0, station_to_m=45, trench_width_m=1.2,
        existing_ground_from_m=100, existing_ground_to_m=100.5,
        invert_from_m=98, invert_to_m=98.5, bedding_depth_m=0.15,
        eligible_gravel_reuse=True, measured_existing_gravel_m=0.2,
        verified_acceptance=True,
    )
    kwargs.update(changes)
    return TrenchSegment(**kwargs)


def test_verified_geometry_is_provisional_not_assumed():
    result = calculate_segment(segment())
    assert result.status == "review"
    assert result.mean_excavation_depth_m == pytest.approx(2.15)
    assert result.bank_excavation_m3 == pytest.approx(116.1)
    assert result.recoverable_gravel_bank_m3 == pytest.approx(8.1)


def test_missing_survey_blocks_total():
    report = calculate_run([segment(invert_to_m=None)])
    assert report["status"] == "blocked"
    assert report["bank_excavation_m3"] is None


def test_reuse_requires_acceptance():
    assert calculate_segment(segment(verified_acceptance=False)).recoverable_gravel_bank_m3 == 0


def test_elevation_errors_are_rejected():
    with pytest.raises(ValueError):
        calculate_segment(segment(invert_from_m=105))


def test_revision_required():
    with pytest.raises(ValueError):
        calculate_segment(segment(sheet_revision=""))


def test_station_gap_is_reported():
    result = calculate_run([segment(), segment(station_from_m=46, station_to_m=90)])
    assert any("Station gap" in warning for warning in result["issues"])


def test_one_manhole_per_good_condition_pipe_day_not_double_counted():
    assert owner_crew_pipe_days(450, 10)["crew_days"] == 10
    assert owner_crew_pipe_days(450, 12)["crew_days"] == 12
    assert owner_crew_pipe_days(450, 10, production_factor=0.5)["pipe_days"] == 20
