# Document Audit Access Control

## Purpose

Document audit data can expose filenames, project identifiers, user identifiers, request correlation IDs, and operational activity. Access is therefore controlled separately from ordinary document browsing.

## Request role header

Audit endpoints read the caller role from the `X-IHOS-Role` request header. Role values are normalized to lowercase snake case. A missing or unknown role is treated as `viewer` and receives no audit permissions.

This header is an integration boundary, not a complete identity system. Production deployments must set it from a trusted authentication gateway or verified application session. It must not be accepted directly from an untrusted public client.

## Role matrix

| Role | Read events | Export CSV | Administer audit data |
|---|---:|---:|---:|
| `admin` | Yes | Yes | Yes |
| `operations_manager` | Yes | Yes | No |
| `estimator` | Yes | No | No |
| `viewer` | No | No | No |

## Protected endpoints

- `GET /api/v1/documents/audit-events` requires `read`.
- `GET /api/v1/documents/audit-events/summary` requires `read`.
- `GET /api/v1/documents/audit-events/export.csv` requires `export`.

## Denied access events

A denied permission check emits a structured document-audit event:

- action: `audit_access`
- outcome: `denied`
- actor: normalized role
- metadata: requested permission

Operators should filter the audit stream by `action=audit_access` and `outcome=denied` when investigating repeated unauthorized attempts.

## Deployment requirements

1. Terminate authentication before requests reach the API.
2. Derive the IHOS role from a verified user or service identity.
3. Remove any inbound public `X-IHOS-Role` header and replace it with the trusted role.
4. Use the JSONL audit store only for single-node deployments with protected persistent storage.
5. Move to a centralized append-only audit service before multi-instance production deployment.
6. Restrict audit CSV exports because they can aggregate sensitive operational metadata.

## Verification

Backend tests cover role normalization, permission snapshots, successful authorization, denied authorization, denial-event emission, and endpoint-level role enforcement.
