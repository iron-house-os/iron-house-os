# Build 184 — Drawing Index

Status: complete

The drawing index contract standardizes sheet records for retrieval and revision control.

## Required fields
- Sheet number and title.
- Discipline and project phase.
- Revision and issue date.
- Current or superseded state.
- Linked project, tender, and source document.

## Acceptance criteria
- Sheet number and title are searchable.
- New revisions supersede prior revisions without deleting history.
- Project views show only current sheets by default with an option to inspect history.
