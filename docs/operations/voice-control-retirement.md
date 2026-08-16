# Voice-control retirement

## Decision

On 2026-08-16 Jeremie Peters directed that the complete Iron House OS browser voice-control system be removed. Physical acceptance on an iPad Air 11-inch (M2), iPadOS 26.6, produced zero successful commands. Prior attempts had also failed to produce a dependable field workflow.

## Supported interaction

- Iron House Chat remains a typed, management-only, read-only assistant.
- Standard touch, pointer, keyboard, and navigation controls remain supported.
- IHOS does not request microphone access, construct browser speech-recognition sessions, synthesize spoken assistant responses, or expose voice-control configuration.

## Release control

Voice-control code, UI, build flags, tests, telemetry, and physical-device acceptance gates must not be restored without a new owner-approved issue and a materially different technical approach. Historical build documents are retained only for audit provenance.

Production deployment remains separately approval-gated.
