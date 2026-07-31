# Iron House OS Agent Policy

This repository is enrolled in the Iron House shared agent framework defined in `agents/README.md`.

## Purpose

Iron House OS is the core operating system for Iron House Civil Constructors, including estimating, suppliers, safety, finance, project operations, and staged deployment workflows.

## Required workflow

- Work only on issue-linked branches.
- Open draft pull requests for all autonomous changes.
- Run the repository's documented build, lint, test, and readiness checks before marking work complete.
- Preserve the locked visual design unless the owner explicitly approves a redesign.
- Keep production deployment behind explicit owner approval.

## Protected boundaries

Agents must not autonomously:

- modify the production droplet or production environment files;
- deploy to `https://os.ironhousecivil.com`;
- change production DNS, certificates, authentication, backups, or database contents;
- rotate or reveal secrets;
- approve or merge their own pull requests;
- change financial assumptions, owner compensation, supplier defaults, estimating policy, or safety policy without an approved issue.

## Staging-first rule

All application and infrastructure changes must be validated in staging or a disposable local environment before production approval is requested.

## Agent priorities

1. CI stability and reproducible builds.
2. Staging readiness and regression testing.
3. Security, authorization, and secret handling.
4. Estimating, supplier, safety, and operational workflow correctness.
5. Documentation and recovery instructions.
