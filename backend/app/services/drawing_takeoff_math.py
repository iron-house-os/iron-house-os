"""Evidence-checked drawing takeoff math. No OCR/geometry recognition or guessed levels."""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite


@dataclass(frozen=True)
class TrenchSegment:
    """A surveyed station segment. All dimensions and elevations are metres, same datum."""
    sheet_revision: str
    drawing_reference: str
    station_from_m: float
    station_to_m: float
    trench_width_m: float
    existing_ground_from_m: float | None
    existing_ground_to_m: float | None
    invert_from_m: float | None
    invert_to_m: float | None
    bedding_depth_m: float
    eligible_gravel_reuse: bool = False
    measured_existing_gravel_m: float = 0.0
    verified_acceptance: bool = False


@dataclass(frozen=True)
class SegmentResult:
    drawing_reference: str
    revision: str
    length_m: float
    mean_excavation_depth_m: float | None
    bank_excavation_m3: float | None
    recoverable_gravel_bank_m3: float
    status: str
    warnings: tuple[str, ...]


def calculate_segment(segment: TrenchSegment, *, max_reuse_depth_m: float = 0.15) -> SegmentResult:
    """Depth and bank volume from cited endpoint levels. No assumed ground/inverts.

    The 150 mm cap is not proof of suitable gravel; both measurement and acceptance
    are required. Bedding is a preliminary below-invert allowance only, and the
    engineer/estimator must confirm actual pipe outside diameter and trench bottom.
    """
    if not segment.drawing_reference.strip() or not segment.sheet_revision.strip():
        raise ValueError("Drawing reference and revision are required")
    if not all(isfinite(v) for v in (segment.station_from_m, segment.station_to_m)):
        raise ValueError("Stations must be finite")
    length = segment.station_to_m - segment.station_from_m
    if length <= 0 or not isfinite(segment.trench_width_m) or segment.trench_width_m <= 0:
        raise ValueError("Stations and width must define a positive trench")
    if not isfinite(segment.bedding_depth_m) or segment.bedding_depth_m < 0:
        raise ValueError("Bedding thickness cannot be negative")
    if not isfinite(max_reuse_depth_m) or max_reuse_depth_m < 0:
        raise ValueError("Gravel reuse limit cannot be negative")
    if not isfinite(segment.measured_existing_gravel_m) or segment.measured_existing_gravel_m < 0:
        raise ValueError("Measured existing gravel cannot be negative")
    levels = (
        segment.existing_ground_from_m, segment.existing_ground_to_m,
        segment.invert_from_m, segment.invert_to_m,
    )
    if any(v is None for v in levels):
        return SegmentResult(segment.drawing_reference, segment.sheet_revision, length,
                             None, None, 0, "blocked",
                             ("Missing ground/invert survey: no excavation volume calculated.",))
    if not all(isfinite(v) for v in levels):
        raise ValueError("Elevations must be finite")
    ground_from, ground_to, invert_from, invert_to = levels
    depth_from = ground_from - invert_from + segment.bedding_depth_m
    depth_to = ground_to - invert_to + segment.bedding_depth_m
    if depth_from <= 0 or depth_to <= 0:
        raise ValueError("Nonpositive excavation depth: verify survey datum and inverts")
    mean_depth = (depth_from + depth_to) / 2
    volume = length * segment.trench_width_m * mean_depth
    reusable = segment.eligible_gravel_reuse and segment.verified_acceptance
    reusable_depth = (
        min(segment.measured_existing_gravel_m, max_reuse_depth_m, depth_from, depth_to)
        if reusable else 0
    )
    warnings: list[str] = []
    if segment.eligible_gravel_reuse and not segment.verified_acceptance:
        warnings.append("Gravel reuse excluded pending acceptance/suitability.")
    if reusable and segment.measured_existing_gravel_m > max_reuse_depth_m:
        warnings.append("Gravel capped at authorized recovery depth.")
    warnings.append(
        "Review intermediate grade breaks, pipe OD, trench bottom, bedding and widths."
    )
    return SegmentResult(segment.drawing_reference, segment.sheet_revision, length,
                         mean_depth, volume, length * segment.trench_width_m * reusable_depth,
                         "review", tuple(warnings))


def calculate_run(segments: list[TrenchSegment]) -> dict:
    """Do not present complete run volume if a segment is missing required geometry."""
    if not segments:
        return {"status": "blocked", "length_m": 0, "bank_excavation_m3": None,
                "gravel_reuse_bank_m3": 0, "issues": ["No measured segments supplied."]}
    results = [calculate_segment(s) for s in segments]
    issues = [
        f"{r.drawing_reference}: {warning}"
        for r in results for warning in r.warnings
    ]
    for previous, current in zip(segments, segments[1:]):
        if abs(previous.station_to_m - current.station_from_m) > 0.001:
            issues.append("Station gap or overlap; revise segmented takeoff.")
    blocked = any(r.status == "blocked" for r in results)
    if blocked:
        issues.append("Run volume withheld because one or more station segments lack levels.")
    return {
        "status": "blocked" if blocked else "review",
        "length_m": sum(r.length_m for r in results),
        "bank_excavation_m3": (
            None if blocked else sum(r.bank_excavation_m3 for r in results)
        ),
        "gravel_reuse_bank_m3": (
            0 if blocked else sum(r.recoverable_gravel_bank_m3 for r in results)
        ),
        "issues": issues,
    }


def owner_crew_pipe_days(
    pipe_length_m: float,
    manholes: int,
    *,
    pipe_m_per_day: float = 45,
    manholes_included_per_pipe_day: int = 1,
    production_factor: float = 1,
) -> dict:
    """Good conditions: 45 m + one ordinary manhole per crew-day, no double count."""
    if any(not isfinite(v) for v in (pipe_length_m, pipe_m_per_day, production_factor)):
        raise ValueError("Production inputs must be finite")
    if pipe_length_m < 0 or pipe_m_per_day <= 0 or not 0 < production_factor <= 1:
        raise ValueError("Invalid production inputs")
    if manholes < 0 or manholes_included_per_pipe_day < 0:
        raise ValueError("Manhole quantities cannot be negative")
    pipe_days = ceil(pipe_length_m / (pipe_m_per_day * production_factor))
    extra = max(0, manholes - pipe_days * manholes_included_per_pipe_day)
    return {
        "pipe_days": pipe_days,
        "additional_structure_days": extra,
        "crew_days": pipe_days + extra,
        "basis": "good-condition planning only; verify structure complexity",
    }
