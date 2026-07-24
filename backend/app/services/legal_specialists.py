from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Specialist:
    key: str
    name: str
    mandate: str
    triggers: tuple[str, ...]


SPECIALISTS = (
    Specialist("intake", "Legal Intake & Privilege Coordinator", "Triage, scope, confidentiality and counsel handoff.", ()),
    Specialist("contracts", "Construction Contracts Counsel Assistant", "Prime contracts, subcontracts, change orders and drafting.", ("contract", "clause", "change order", "scope")),
    Specialist("lien_payment", "Builders Lien & Payment Analyst", "Holdback, lien, payment and collection risk.", ("lien", "holdback", "payment", "invoice")),
    Specialist("tender", "Tender & Procurement Analyst", "Tender rules, bid compliance and procurement fairness.", ("tender", "bid", "rfp", "procurement")),
    Specialist("subcontract", "Subcontract & Supplier Analyst", "Trade scope, flow-down, purchase orders and supplier terms.", ("subcontract", "supplier", "purchase order", "vendor")),
    Specialist("employment", "Employment & Labour Analyst", "Employment standards, discipline and workplace agreements.", ("employee", "termination", "overtime", "wage")),
    Specialist("ohs", "WorkSafeBC & OHS Analyst", "Construction safety duties, incidents and regulatory response.", ("worksafe", "safety", "incident", "excavation")),
    Specialist("corporate", "Corporate Governance Analyst", "Corporate authority, records and signing controls.", ("director", "shareholder", "corporate", "signing")),
    Specialist("privacy_ai", "Privacy & AI Governance Analyst", "Personal information, AI use and information governance.", ("privacy", "personal information", "ai", "recording")),
    Specialist("insurance", "Insurance & Risk Transfer Analyst", "Insurance, indemnity, bonding and risk transfer.", ("insurance", "indemnity", "bond", "waiver")),
    Specialist("disputes", "Claims, Disputes & Collections Analyst", "Claims strategy, notices, evidence and limitation risk.", ("claim", "dispute", "demand", "collection")),
    Specialist("environment", "Environmental & Heritage Analyst", "Contamination, spill, heritage and permitting risk.", ("environment", "spill", "contamination", "archaeological")),
    Specialist("transport", "Transportation & Fleet Compliance Analyst", "Commercial vehicle, driver and load compliance.", ("truck", "driver", "cvse", "load")),
)

AUTHORITIES = (
    {"id": "bc-builders-lien-act", "title": "BC Builders Lien Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_97045_01", "status": "active", "jurisdiction": "BC"},
    {"id": "bc-prompt-payment-act", "title": "BC Construction Prompt Payment Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/25024", "status": "not_in_force", "jurisdiction": "BC"},
    {"id": "bc-employment-standards-act", "title": "BC Employment Standards Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/00_96113_01", "status": "active", "jurisdiction": "BC"},
    {"id": "bc-workers-compensation-act", "title": "BC Workers Compensation Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/19001_00_multi", "status": "active", "jurisdiction": "BC"},
    {"id": "worksafebc-ohs-part-20", "title": "WorkSafeBC OHS Regulation Part 20", "url": "https://www.worksafebc.com/en/law-policy/occupational-health-safety/searchable-ohs-regulation/ohs-regulation/part-20-construction-excavation-and-demolition", "status": "active", "jurisdiction": "BC"},
    {"id": "bc-business-corporations-act", "title": "BC Business Corporations Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/02057_00_multi", "status": "active", "jurisdiction": "BC"},
    {"id": "bc-pipa", "title": "BC Personal Information Protection Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/03063_01", "status": "active", "jurisdiction": "BC"},
    {"id": "federal-pipeda", "title": "Personal Information Protection and Electronic Documents Act", "url": "https://laws-lois.justice.gc.ca/eng/acts/P-8.6/", "status": "active", "jurisdiction": "Canada"},
    {"id": "bc-limitation-act", "title": "BC Limitation Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/12013_01", "status": "active", "jurisdiction": "BC"},
    {"id": "bc-environmental-management-act", "title": "BC Environmental Management Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/03053_06", "status": "active", "jurisdiction": "BC"},
    {"id": "bc-heritage-conservation-act", "title": "BC Heritage Conservation Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96187_01", "status": "active", "jurisdiction": "BC"},
    {"id": "bc-commercial-transport-act", "title": "BC Commercial Transport Act", "url": "https://www.bclaws.gov.bc.ca/civix/document/id/complete/statreg/96058_01", "status": "active", "jurisdiction": "BC"},
)


def specialist_catalogue() -> list[dict]:
    return [{**asdict(item), "triggers": list(item.triggers)} for item in SPECIALISTS]


def authority_catalogue() -> list[dict]:
    return [dict(item) for item in AUTHORITIES]


def active_authorities() -> list[dict]:
    return [dict(item) for item in AUTHORITIES if item["status"] == "active"]


def triage_specialists(text: str) -> list[str]:
    lowered = text.lower()
    selected = ["intake"]
    selected.extend(item.key for item in SPECIALISTS if item.triggers and any(word in lowered for word in item.triggers))
    return list(dict.fromkeys(selected if len(selected) > 1 else [*selected, "contracts", "disputes"]))

