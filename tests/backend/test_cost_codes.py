import pytest

from app.schemas.cost_code import CostCodeGroup, CostCodeResolveRequest
from app.schemas.estimate import EstimateItemType, EstimateUnit
from app.services.cost_codes import get_cost_code_library, resolve_cost_code


def test_cost_code_library_contains_core_civil_scopes() -> None:
    library = get_cost_code_library()
    by_code = {item.code: item for item in library.items}

    assert library.version == "2026.08"
    assert by_code["02-200"].name == "Common excavation"
    assert by_code["03-100"].default_unit == EstimateUnit.metre
    assert by_code["05-100"].default_item_type == EstimateItemType.subcontract
    assert by_code["06-100"].group == CostCodeGroup.traffic
    assert len(library.items) == len(by_code)


def test_cost_code_library_separates_storm_sanitary_and_shallows() -> None:
    library = get_cost_code_library()
    by_code = {item.code: item for item in library.items}

    assert by_code["03-100"].name == "Storm main installation"
    assert by_code["03-110"].name == "Storm service installation"
    assert by_code["03-500"].name == "Sanitary main installation"
    assert by_code["03-510"].name == "Sanitary service installation"
    assert by_code["03-200"].name == "Water main installation"
    assert by_code["03-210"].name == "Water service installation"
    assert by_code["10-100"].name == "Shallows - Hydro and communications installation"
    assert by_code["10-100"].group == CostCodeGroup.shallows
    assert by_code["10-200"].name == "Shallows - Streetlight installation"
    assert by_code["10-200"].group == CostCodeGroup.shallows
    assert "10-300" not in by_code


def test_cost_code_resolver_distinguishes_utility_mains_and_services() -> None:
    cases = {
        "install storm main": "03-100",
        "install storm service": "03-110",
        "install sanitary main": "03-500",
        "install sanitary service": "03-510",
        "install water main": "03-200",
        "install water service": "03-210",
        "install hydro conduit": "10-100",
        "install communications duct": "10-100",
        "install streetlight conduit": "10-200",
    }

    for description, expected_code in cases.items():
        result = resolve_cost_code(CostCodeResolveRequest(description=description))
        assert result.match is not None
        assert result.match.code == expected_code


def test_cost_code_resolver_matches_exact_code() -> None:
    result = resolve_cost_code(CostCodeResolveRequest(code="03-300"))

    assert result.match is not None
    assert result.match.name == "Manholes"
    assert result.confidence == 1.0


def test_cost_code_resolver_matches_civil_description() -> None:
    result = resolve_cost_code(
        CostCodeResolveRequest(description="Supply and install asphalt paving")
    )

    assert result.match is not None
    assert result.match.code == "05-100"
    assert result.confidence >= 0.7


def test_cost_code_resolver_returns_no_match_for_unknown_scope() -> None:
    result = resolve_cost_code(CostCodeResolveRequest(description="specialty unrelated scope xyz"))

    assert result.match is None
    assert result.confidence == 0


def test_cost_code_resolve_request_requires_search_input() -> None:
    with pytest.raises(ValueError):
        CostCodeResolveRequest()
