# Project job numbering

IHOS assigns a permanent job number when a project first becomes `awarded`.

## Number format

- Default: `IH-YYYY-NNN`
- Example: `IH-2026-001`
- The three-digit sequence restarts for each award year using the Iron House BC business date and expands beyond three digits when required.

## Allocation rules

1. An opportunity or tender may remain unnumbered.
2. Creating an awarded project without a number assigns the next number for the current year.
3. Changing an existing project to awarded assigns the next number if the project is still unnumbered.
4. An existing or explicitly supplied project number is preserved.
5. Later status changes do not remove or replace the assigned number.
6. The database uniqueness constraint and allocation retry prevent two awarded projects from retaining the same number.

Existing legacy projects are not renumbered automatically. Any controlled legacy cleanup must be reviewed separately before changing company records.
