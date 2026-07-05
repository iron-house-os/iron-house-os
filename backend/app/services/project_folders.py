from __future__ import annotations

import re
from datetime import date

from app.schemas.project_folder import ProjectFolderEntry, ProjectFolderManifest, ProjectFolderRequest


PROJECT_FOLDER_STRUCTURE: tuple[tuple[str, str], ...] = (
    ("00_Admin", "Administrative project information."),
    ("01_Tender_Documents", "Tender documents and forms."),
    ("02_Drawings", "Drawing package."),
    ("02_Drawings/Current", "Current drawings."),
    ("02_Drawings/Superseded", "Superseded drawings."),
    ("02_Drawings/Extracted_Sheets", "Trade-specific drawing extracts."),
    ("02_Drawings/Markups", "Drawing markups."),
    ("03_Addenda", "Addenda and clarifications."),
    ("04_Standards_and_Specs", "Standards and specifications."),
    ("05_Takeoff", "Quantity takeoff files."),
    ("06_Estimate", "Estimate files."),
    ("07_RFQs", "Outgoing RFQ packages."),
    ("07_RFQs/Pipe_Utilities", "Pipe and utility RFQs."),
    ("07_RFQs/Structures", "Structure RFQs."),
    ("07_RFQs/Aggregates", "Aggregate RFQs."),
    ("07_RFQs/Asphalt", "Asphalt RFQs."),
    ("07_RFQs/Concrete", "Concrete RFQs."),
    ("07_RFQs/Traffic_Control", "Traffic-control RFQs."),
    ("07_RFQs/Testing", "Testing RFQs."),
    ("07_RFQs/Electrical_Lighting", "Electrical and lighting RFQs."),
    ("07_RFQs/Landscaping", "Landscaping RFQs."),
    ("07_RFQs/Trucking_Disposal", "Trucking and disposal RFQs."),
    ("08_Supplier_Quotes", "Supplier quotes."),
    ("09_Subcontractor_Quotes", "Subcontractor quotes."),
    ("10_Correspondence", "Project correspondence."),
    ("10_Correspondence/Owner_Consultant", "Owner and consultant correspondence."),
    ("10_Correspondence/Suppliers", "Supplier correspondence."),
    ("10_Correspondence/Subcontractors", "Subcontractor correspondence."),
    ("10_Correspondence/RFIs", "RFIs and clarifications."),
    ("10_Correspondence/Internal_Notes", "Internal notes."),
    ("11_Submission", "Final submission package."),
    ("12_Post_Bid", "Post-bid review."),
    ("13_Award_Handoff", "Award handoff package."),
    ("99_Archive", "Archive."),
)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "", value.strip())
    return cleaned or "Project"


def build_root_folder_name(close_date: date, owner: str, project_code: str, project_name: str) -> str:
    return f"{close_date.isoformat()}_{_slug(owner)}_{_slug(project_code)}_{_slug(project_name)}"


def build_project_index(payload: ProjectFolderRequest, root_folder: str) -> str:
    return f"""# Project Index

Project: {payload.project_name}
Project Code: {payload.project_code}
Owner / Municipality: {payload.owner}
Consultant: {payload.consultant or ""}
Closing Date: {payload.close_date.isoformat()}
Bid Status: New
Estimator: {payload.estimator or ""}
Root Folder: {root_folder}

## Key Files
Tender Documents:
Current Drawings:
Addenda:
Takeoff:
Estimate:
RFQ Log:
Submission:

## Key Risks
-

## Open RFIs
-

## Bid Qualifications
-
"""


def build_project_folder_manifest(payload: ProjectFolderRequest) -> ProjectFolderManifest:
    root_folder = build_root_folder_name(
        close_date=payload.close_date,
        owner=payload.owner,
        project_code=payload.project_code,
        project_name=payload.project_name,
    )
    entries = [
        ProjectFolderEntry(path=f"{root_folder}/{path}", kind="folder", description=description)
        for path, description in PROJECT_FOLDER_STRUCTURE
    ]
    entries.append(
        ProjectFolderEntry(
            path=f"{root_folder}/PROJECT_INDEX.md",
            kind="file",
            description="Project index template.",
        )
    )
    return ProjectFolderManifest(
        root_folder=root_folder,
        entries=entries,
        project_index=build_project_index(payload, root_folder),
    )
