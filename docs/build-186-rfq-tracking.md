# Build 186 — RFQ Tracking

Status: complete

RFQ tracking records supplier delivery and response state at the project level.

## Required states
- Draft
- Ready
- Sent
- Received
- Declined
- Overdue
- Cancelled

## Required dates
- Created
- Sent
- Quote due
- Last reminder
- Response received

Reminder logic must be idempotent and must not send messages automatically until an outbound email connector is explicitly enabled.
