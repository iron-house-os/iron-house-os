# Release readiness trigger

This non-executable marker intentionally triggers the existing GitHub CI and Release Readiness workflows for the current approved `main` release after documentation-only commits advanced `main` without matching the Release Readiness path filters.

It does not change application runtime behaviour, deployment configuration, credentials, database schema, or production controls.

Approved purpose: generate fresh release evidence through the normal IHOS quality gates before production deployment.
