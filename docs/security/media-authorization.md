# Media authorization boundary

Issue #112 introduces shared photo assets, immutable originals, version history, and
record links. Every media API route requires an authenticated principal. Asset
metadata, history, current content, prior-version content, and downloads all use the
same service-level authorization check.

IHOS does not yet model explicit user-to-project assignments. Until that relationship
exists, media access fails closed for non-management roles:

- administrators and operations managers can access media across projects;
- estimators and viewers can list, inspect, edit, restore, or download only assets
  whose `created_by_id` matches their authenticated principal;
- unauthorized asset reads return `404` so asset existence, metadata, versions, and
  links are not disclosed;
- list filters are always combined with the ownership boundary, including project,
  record, and source-document filters;
- location metadata is returned only to administrators and operations managers.

This ownership fallback is intentionally narrower than a future project-assignment
model. It must not be broadened until an approved user-to-project membership source
exists and is enforced by the media service.

Record links are also fail closed. For records that carry a project (`field_record`,
`vehicle_log`, `financial_entry`, `document`, and `project`), the record project must
exactly match the media asset project. Project metadata cannot be reassigned when an
existing project-scoped link would become inconsistent. Equipment and startup expense
records do not currently carry project IDs, so they remain governed by asset ownership
and role access until those models gain a project relationship.
