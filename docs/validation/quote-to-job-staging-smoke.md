# Quote-to-job disposable staging smoke

## Purpose

The release-readiness workflow validates the complete Customer Quote to awarded-job path through the deployed HTTP stack. This provides a browser-independent acceptance route when cloud-browser or iPad tooling is unavailable.

## Safety boundary

The extended lifecycle runs only when both flags are present:

```text
STAGING_SYNTHETIC_DATA=true
STAGING_MVP_SYNTHETIC_DATA=true
```

The GitHub release-readiness workflow sets both flags only inside its disposable Docker staging stack. The ordinary shared-staging deployment does not enable the lifecycle. Running the script without administrator credentials fails before synthetic data is created.

All request payloads and session cookies live in a permission-restricted `mktemp` directory and are removed on exit. The synthetic suffix accepts only letters, digits, dots, underscores, and hyphens.

## Verified lifecycle

1. Authenticate the disposable staging administrator.
2. Create a uniquely named Customer Quote and linked opportunity.
3. Verify the draft has a record revision and no job number.
4. Record the quote as sent and verify it remains non-binding.
5. Record management acceptance with an explicit disposable-staging reference.
6. Verify the accepted quote has a generated `IH-` job number.
7. Verify the linked project is awarded and its job number matches.
8. Verify the awarded workspace exists.
9. Verify all ten project-start controls exist and begin unchecked/not ready.
10. Verify the launch dashboard matches the job and identifies the next control without inferring readiness.
11. Authenticate a synthetic viewer and verify the launch dashboard is denied with HTTP 403.

Any unexpected HTTP status or state mismatch stops the release gate. Generated quote, project, revision, and job identifiers are parsed from API responses rather than assumed.

## Manual use

The base smoke remains safe for shared staging when the MVP synthetic flag is omitted. Do not enable `STAGING_MVP_SYNTHETIC_DATA` against shared staging without a separately approved test-data plan because accepted quotes are intentionally immutable and allocate permanent staging job numbers.
