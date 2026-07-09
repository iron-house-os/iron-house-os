# File Upload Plan

## MVP goal

Allow estimators to upload drawings, specifications, addenda, RFQ attachments, quotes, and bid backup files.

## Required behavior

- Upload file.
- Attach file to project.
- Assign category.
- Store metadata.
- Mark document status.
- Retrieve file for review.
- Include file in RFQ package selection.

## Storage options

1. Local filesystem for development only.
2. Private object storage for hosted use.
3. Google Drive integration later if approved.

## Controls

- Restrict file extensions.
- Limit file size.
- Avoid public URLs.
- Store original filename and safe storage key separately.
- Add upload audit event.
