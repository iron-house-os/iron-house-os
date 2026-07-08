from app.schemas.municipality import MunicipalityCheckRequest, MunicipalityCheckResponse, MunicipalityRequirement

COMMON_REQUIREMENTS = [
    MunicipalityRequirement(
        municipality="common",
        category="testing",
        title="Compaction and material testing allowance",
        description="Civil tenders commonly require third-party compaction, asphalt, concrete, and material testing documentation.",
        scopes=["earthworks", "roadworks", "asphalt", "concrete", "storm", "sanitary", "water"],
        cost_impact="medium",
        estimating_note="Carry testing allowance or subcontract quote for density testing, Proctors, asphalt cores, and concrete breaks where applicable.",
        rfq_note="Send scope to preferred testing agency with schedule and expected quantities.",
    ),
    MunicipalityRequirement(
        municipality="common",
        category="traffic_control",
        title="Traffic management plan and TCP coverage",
        description="Work in municipal roads typically requires traffic control plans, certified personnel, signage, and lane closure coordination.",
        scopes=["traffic", "roadworks", "asphalt", "storm", "sanitary", "water"],
        cost_impact="high",
        estimating_note="Include TCP preparation, setup/removal, lane closure labour, signs, delineators, and potential night/weekend premiums.",
        rfq_note="Request traffic control quote with work windows and expected staging.",
    ),
    MunicipalityRequirement(
        municipality="common",
        category="esc",
        title="Erosion and sediment control",
        description="Projects disturbing soil often require ESC measures, maintenance, and weather response.",
        scopes=["earthworks", "storm", "roadworks", "landscape"],
        cost_impact="medium",
        estimating_note="Carry silt fence, catch basin protection, inlet bags, check dams, maintenance visits, and storm response allowance.",
    ),
]

MUNICIPAL_REQUIREMENTS = {
    "surrey": [
        MunicipalityRequirement(
            municipality="surrey",
            category="restoration",
            title="MMCD supplementary restoration expectations",
            description="Surrey supplementary standards can affect trench restoration, asphalt limits, boulevard repairs, and inspection documentation.",
            scopes=["roadworks", "asphalt", "storm", "sanitary", "water", "landscape"],
            cost_impact="high",
            estimating_note="Review Surrey supplementary MMCD requirements before pricing pavement restoration, boulevard reinstatement, and approved products.",
        ),
        MunicipalityRequirement(
            municipality="surrey",
            category="approved_materials",
            title="Approved materials and utility products",
            description="Utility products may need to match City approved materials and details.",
            scopes=["storm", "sanitary", "water"],
            cost_impact="medium",
            estimating_note="Confirm pipe, fittings, manholes, valves, hydrants, frames/covers, and catch basins against accepted products before issuing RFQs.",
            rfq_note="Ask suppliers to confirm compliance with City of Surrey approved products and MMCD supplementary requirements.",
        ),
    ],
    "vancouver": [
        MunicipalityRequirement(
            municipality="vancouver",
            category="permits",
            title="Street use and work window constraints",
            description="Urban work may require street use permits, limited work windows, notification, and additional traffic management.",
            scopes=["traffic", "roadworks", "asphalt", "concrete", "storm", "sanitary", "water"],
            cost_impact="high",
            estimating_note="Carry permit/admin time, constrained access productivity loss, and traffic control premiums.",
        )
    ],
    "burnaby": [
        MunicipalityRequirement(
            municipality="burnaby",
            category="inspections",
            title="Inspection hold points",
            description="Municipal inspection sequencing can create hold points for utilities, subgrade, forms, concrete, asphalt, and restoration.",
            scopes=["storm", "sanitary", "water", "roadworks", "concrete", "asphalt"],
            cost_impact="medium",
            estimating_note="Carry coordination time and schedule float for inspection hold points.",
        )
    ],
    "richmond": [
        MunicipalityRequirement(
            municipality="richmond",
            category="esc",
            title="Low grade drainage and dewatering risk",
            description="Richmond projects can require additional attention to drainage, groundwater, and sediment controls.",
            scopes=["earthworks", "storm", "roadworks"],
            cost_impact="high",
            estimating_note="Review groundwater/dewatering assumptions and carry pumps, treatment, and standby allowance where needed.",
        )
    ],
    "delta": [
        MunicipalityRequirement(
            municipality="delta",
            category="restoration",
            title="Road and boulevard restoration coordination",
            description="Restoration limits and inspection requirements can materially affect asphalt, concrete, and landscape pricing.",
            scopes=["roadworks", "asphalt", "concrete", "landscape"],
            cost_impact="medium",
            estimating_note="Confirm restoration limits and include sawcut, grind, tack, asphalt, concrete, topsoil, and sod allowances.",
        )
    ],
    "langley": [
        MunicipalityRequirement(
            municipality="langley",
            category="approved_materials",
            title="Township/City utility material confirmation",
            description="Langley-area projects may require specific approved products and inspection coordination by jurisdiction.",
            scopes=["storm", "sanitary", "water"],
            cost_impact="medium",
            estimating_note="Confirm whether the work is in City or Township jurisdiction and verify approved utility materials.",
        )
    ],
    "abbotsford": [
        MunicipalityRequirement(
            municipality="abbotsford",
            category="compaction",
            title="Backfill and compaction documentation",
            description="Backfill, trench reinstatement, and density records should be accounted for in utility and roadwork pricing.",
            scopes=["earthworks", "storm", "sanitary", "water", "roadworks"],
            cost_impact="medium",
            estimating_note="Carry compaction testing, imported backfill risk, and documentation time.",
        )
    ],
    "chilliwack": [
        MunicipalityRequirement(
            municipality="chilliwack",
            category="documentation",
            title="As-built and closeout documentation",
            description="Closeout records, redlines, inspections, and test results should be included in bid assumptions.",
            scopes=["storm", "sanitary", "water", "roadworks", "concrete", "asphalt"],
            cost_impact="low",
            estimating_note="Carry admin/field time for as-builts, redlines, inspection records, and test result turnover.",
        )
    ],
}


def check_municipality(payload: MunicipalityCheckRequest) -> MunicipalityCheckResponse:
    municipality_key = payload.municipality.strip().lower()
    requirements = [*COMMON_REQUIREMENTS, *MUNICIPAL_REQUIREMENTS.get(municipality_key, [])]
    if payload.project_scopes:
        scope_set = set(payload.project_scopes)
        requirements = [requirement for requirement in requirements if scope_set.intersection(requirement.scopes)]

    warnings: list[str] = []
    if municipality_key not in MUNICIPAL_REQUIREMENTS:
        warnings.append("No municipality-specific rule set found; common civil requirements only.")
    if not payload.project_scopes:
        warnings.append("No project scopes selected; showing broad municipality checklist.")

    return MunicipalityCheckResponse(
        municipality=payload.municipality,
        project_scopes=payload.project_scopes,
        requirement_count=len(requirements),
        high_impact_count=sum(1 for requirement in requirements if requirement.cost_impact == "high"),
        requirements=requirements,
        warnings=warnings,
    )
