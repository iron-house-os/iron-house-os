# Emergency action card field access

Issue #70 Phase 4 adds two field-safe access paths for emergency action cards.

## QR field link

The Safety Operations register creates a QR code from a stable IHOS deep link. The QR contains no password, access token or emergency-card content. Existing IHOS authentication and role checks still apply after scanning.

## Offline PDF

Authorized users can download a compact emergency action card PDF for local offline storage or printing. The PDF is a point-in-time copy, not a second source of truth. It tells the user to confirm the current online record after connectivity returns and replace the copy when site conditions change.

IHOS deliberately does not cache authenticated safety responses in a service worker. This avoids leaving hidden safety records on a shared field device after sign-out.
