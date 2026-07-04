from dataclasses import dataclass


@dataclass(frozen=True)
class AgentCapability:
    key: str
    description: str
    enabled: bool = False


PHASE_TWO_AGENT_CAPABILITIES = [
    AgentCapability("drawing_ingestion", "Parse drawing packages and prepare takeoff inputs."),
    AgentCapability("supplier_outreach", "Coordinate RFQ communication with supplier contacts."),
    AgentCapability("tender_monitoring", "Track public tender sources and normalize opportunities."),
    AgentCapability("standards_lookup", "Map municipality standards to project requirements."),
]
