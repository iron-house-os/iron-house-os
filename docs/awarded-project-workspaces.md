# Awarded project workspaces

When a project first becomes `awarded`, IHOS assigns its permanent job number and prepares one internal standard workspace manifest and one [awarded project start checklist](awarded-project-start-checklist.md) in the same database transaction.

## Rules

1. The root identity is `[job number]_[project name]`, with unsafe path characters removed.
2. The manifest contains the standard folders from `Documentation/PROJECT_FOLDER_STANDARD.md` and a generated `PROJECT_INDEX.md`.
3. The saved root is immutable setup evidence. Renaming or advancing the project later does not rename or duplicate the workspace. Explicit safety-launch initialization may add the single controlled `13_Award_Handoff/Safety` manifest entry when it is absent. The first approved, ready field-production post may add the controlled `13_Award_Handoff/Field_Production` hierarchy. Retries do not duplicate or rewrite other entries.
4. Opportunity and tendering records do not receive an awarded workspace.
5. Existing legacy projects are not backfilled automatically.
6. The manifest prepares IHOS project organization only. It does not create Google Drive folders, overwrite documents, or make external storage changes.

The authenticated project endpoint `GET /api/v1/projects/{project_id}/workspace` returns the saved manifest for a provisioned job. Project Workspace shows its stable root and prepared folder list separately from the interactive job-start checklist. A manifest entry prepares only IHOS internal organization; it does not claim that an external Drive folder exists.

Administrators and operations managers may initialize or read the blocked launch shell through `POST /api/v1/projects/{project_id}/safety-launch` and `GET /api/v1/projects/{project_id}/safety-launch`. The generic project create/update routes cannot inject, remove, release, or activate this system-managed control.

The Field Production hierarchy contains `Daily_Reports`, `Photos`, and `Tickets` paths. It is prepared only inside the successful controlled-post transaction. The paths and generated report are internal references; they do not create an external folder or upload a file.
