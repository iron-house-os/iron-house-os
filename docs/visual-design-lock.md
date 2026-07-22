# Iron House OS visual design lock

## Decision

The production appearance released in commit `3c6cbe89c205f6db164b05df59e4df9aa865101b` on 2026-07-22 is the approved Iron House OS visual baseline.

The OS may continue to gain workflows, data, controls, and responsive refinements, but it must not receive a significant visual redesign without explicit written approval from Jeremie Peters.

## Protected visual system

- Brand colours: CAT-inspired gold `#DDAE58`, charcoal `#34373A`, black `#0B0D11`, silver `#D9DCE0`, and the existing iron neutral scale.
- Identity: the current Iron House logo, application icons, and the gold/silver/black presentation.
- Application shell: fixed dark sidebar on desktop, drawer navigation on mobile, white sticky header, light workspace, and the existing content width and spacing.
- Typography: Inter with the existing system-font fallback, current weights, compact uppercase brand labels, and current heading hierarchy.
- Surfaces: white operational cards, restrained borders and shadows, medium corner radii, and dark branded hero panels using the existing gold glow and steel-grid treatment.
- Interaction: gold active-navigation and primary-action states, current signal colours, and the established desktop/mobile behaviour.

## Changes that remain allowed

- New modules and workflow screens that use the protected visual system.
- Content, data, forms, tables, validation, and operational controls.
- Accessibility, responsive, performance, and browser-compatibility fixes that preserve the overall appearance.
- Small spacing or legibility corrections that do not change the OS's visual identity or layout model.

## Changes requiring owner approval

Explicit written approval is required before changing the logo, application icons, core palette, typography family, sidebar/header structure, global density, primary corner-radius or shadow language, branded hero treatment, navigation behaviour, or introducing a new theme or broad restyle.

## Enforcement

`frontend/visual-design-lock.json` records SHA-256 hashes for the protected source and identity assets. Both CI and release readiness run `scripts/check_visual_design_lock.py`. A protected file change fails the build until the manifest is deliberately updated in the same approved pull request.

`CODEOWNERS` requests Iron House owner review for protected files, the manifest, the checker, and this policy. Updating the manifest is an acknowledgement that the visual baseline is changing; it is not routine maintenance.
