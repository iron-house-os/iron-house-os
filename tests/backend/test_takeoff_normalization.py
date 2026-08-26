from app.schemas.takeoff import QuantityItem
from app.schemas.takeoff_normalization import TakeoffNormalizeRequest
from app.services.takeoff_normalization import normalize_takeoff


def test_normalize_combines_duplicate_drawing_quantities() -> None:
    payload = TakeoffNormalizeRequest(
        items=[
            QuantityItem(
                code="03-100",
                description="PVC storm pipe",
                category="pipe",
                quantity=42,
                unit="m",
                confidence=0.95,
                drawing_reference="C-201",
                revision="2",
            ),
            QuantityItem(
                code="03-100",
                description="PVC storm pipe",
                category="pipe",
                quantity=18,
                unit="m",
                confidence=0.9,
                drawing_reference="C-202",
                revision="2",
            ),
        ]
    )

    result = normalize_takeoff(payload)

    assert result.input_count == 2
    assert result.normalized_count == 1
    assert result.normalized_items[0].quantity == 60
    assert result.normalized_items[0].drawing_reference == "C-201, C-202"
    assert result.duplicate_groups[0].item_count == 2
    assert result.estimate_ready_count == 1


def test_normalize_rejects_low_confidence_and_missing_reference() -> None:
    payload = TakeoffNormalizeRequest(
        minimum_confidence=0.8,
        items=[
            QuantityItem(
                description="Unverified excavation",
                category="earthworks",
                quantity=100,
                unit="m3",
                confidence=0.6,
            ),
            QuantityItem(
                description="Sidewalk area",
                category="concrete",
                quantity=55,
                unit="m2",
                confidence=0.95,
            ),
        ],
    )

    result = normalize_takeoff(payload)

    assert result.normalized_count == 0
    assert len(result.rejected_items) == 2
    assert any("below 0.80" in warning for warning in result.warnings)
    assert any("drawing reference is required" in warning for warning in result.warnings)


def test_normalize_preserves_revision_boundaries() -> None:
    payload = TakeoffNormalizeRequest(
        items=[
            QuantityItem(
                code="05-100",
                description="Asphalt paving",
                category="asphalt",
                quantity=20,
                unit="t",
                confidence=1,
                drawing_reference="C-401",
                revision="1",
            ),
            QuantityItem(
                code="05-100",
                description="Asphalt paving",
                category="asphalt",
                quantity=25,
                unit="t",
                confidence=1,
                drawing_reference="C-401",
                revision="2",
            ),
        ]
    )

    result = normalize_takeoff(payload)

    assert result.normalized_count == 2
    assert result.duplicate_groups == []
