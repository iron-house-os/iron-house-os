# Builds 101-110 Document Management

## Completed

- Build 101: Local file storage service with extension validation, size limit, safe filename generation, and SHA-256 hashing.
- Build 102: Document upload, integrity, and RFQ attachment manifest schemas.
- Build 103: Document upload/integrity/manifest backend service functions.
- Build 104: Document upload, download, integrity, and attachment manifest API routes.
- Build 105: Frontend document API client support for upload, download, integrity, and manifests.
- Build 106: Document upload panel.
- Build 107: Project document browser with download and current/superseded controls.
- Build 108: RFQ attachment manifest panel.
- Build 109: Document Operations page, route, and module card.
- Build 110: Document management block documentation.

## New backend endpoints

- `POST /api/v1/documents/upload`
- `GET /api/v1/documents/{document_id}/download`
- `GET /api/v1/documents/{document_id}/integrity`
- `POST /api/v1/documents/attachment-manifest`

## New frontend route

- `/document-operations`

## Capabilities

IHOS can now upload project files, store them locally for development/internal testing, calculate SHA-256 hashes, detect duplicate uploads by hash, download stored files, check file integrity, mark drawing/document status, and build RFQ attachment manifests.

## Remaining before hosted production

- Move file storage from local filesystem to private object storage.
- Add authentication and file permissions.
- Add signed download URLs.
- Add upload audit events.
- Add automated upload/download tests in CI.
