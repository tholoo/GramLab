# Establish the native effects profile and a bounded verification path

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

Own docs/development/android-effects-profile.md (new), this ticket and optional isolated
read-only probe tests/probes/android_effects_profile.py. No production patches, runtime defaults,
source pins, lockfiles or shared docs are delegated.

## Acceptance

- Inspect pinned upstream SharedConfig, LiteMode and blur3 against launcher CPU/GPU/theme settings.
  Explain which measured capabilities/preferences/app-config bits gate chat blur and liquid glass.
- Separate source deductions from observed runtime values and screenshots; no claim of a missing
  renderer or a verified visual fix without native evidence.
- Identify the smallest reproducible native observation and effects-enabled comparison using
  existing dedicated offline tools. Coordinate guest runs with coordinator and android-gate lock.
- Keep host-specific inputs ignored. Preserve upstream rendering and current baseline; propose any
  consequential profile change to coordinator before changing behavior.
- Include expensive-step opportunities backed by existing build/test timings where relevant.
  Commit the bounded findings/probe and report remaining runtime work honestly.
