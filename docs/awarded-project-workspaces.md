# Awarded project workspaces

When a project first becomes `awarded`, IHOS assigns its permanent job number and prepares one internal standard workspace manifest and one [awarded project start checklist](awarded-project-start-checklist.md) in the same database transaction.

## Rules

1. The root identity is `[job number]_[project name]`, with unsafe path characters removed.
2. The manifest contains the standard folders from `Documentation/PROJECT_FOLDER_STANDARD.md` and a generated `PROJECT_INDEX.md`.
3. The saved root and manifest are immutable setup evidence. Renaming or advancing the project later does not rename or duplicate the workspace.
4. Opportunity and tendering records do not receive an awarded workspace.
5. Existing legacy projects are not backfilled automatically.
6. The manifest prepares IHOS project organization only. It does not create Google Drive folders, overwrite documents, or make external storage changes.

The authenticated project endpoint `GET /api/v1/projects/{project_id}/workspace` returns the saved manifest for a provisioned job. Project Workspace shows its stable root and prepared top-level folder list separately from the interactive job-start checklist.
