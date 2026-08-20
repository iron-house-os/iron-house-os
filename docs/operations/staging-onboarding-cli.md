# Staging onboarding CLI

Use `scripts/staging_onboarding.py` when the staging admin UI cannot be operated reliably. The helper is locked to `https://staging.os.ironhousecivil.com` and refuses production and arbitrary hosts.

Run from a current Codespace on `main`:

```bash
python3 scripts/staging_onboarding.py
```

The helper prompts for the staging administrator email and a hidden password. It then confirms that CEO, President, and CFO are available as controlled positions before processing the approved executive test roster one person at a time. Employee emails are entered interactively and are not stored in source code or shell history.

The helper creates onboarding drafts only. It does not issue invitations, complete checklist items, approve records, record orientations, activate portal accounts, or generate temporary passwords. Existing email matches are skipped to prevent duplicate drafts.

After the approved CEO, President, and CFO drafts exist, generate fresh invitation links without re-entering employee emails:

```bash
python3 scripts/staging_onboarding.py invite
```

The invitation action authenticates the staging administrator, finds exactly one matching executive record for each controlled title, and issues a fresh link for each person. A fresh handoff invalidates older links. Current links are written to a mode-`0600` temporary file outside the repository; the terminal prints only that file path. Open the file locally, share each link only with its named employee, and delete the file after handoff.

Invitation generation does not complete or acknowledge employee checklist items. It also does not record orientation evidence, approve onboarding, activate portal access, or create passwords. Each employee must personally complete their checklist, and management must verify the real orientation controls before activation.

Stop with `Ctrl+C` at any prompt. Successfully created drafts remain in staging; no production records are read or changed.
