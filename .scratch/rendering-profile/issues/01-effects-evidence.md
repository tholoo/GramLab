# Establish the native effects profile and a bounded verification path

Type: task
Status: ready-for-agent
Work state: claimed
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

## Answer

[The effects profile](../../../docs/development/android-effects-profile.md) records the exact
performance-class, LiteMode, app-config, power-saver and blur3 gates in the pinned source. The
current two-CPU launcher implies LOW and therefore disables both effects by default, but no live
field or effects-enabled screenshot was observed. The note defines a one-guest baseline/HIGH
comparison through upstream settings, with a separate explicitly authorized liquid-glass bit
comparison. It also explains why the focused application probe is the next check instead of the
roughly 21-minute, 28-test Android gate. No production patch, default or runtime profile changed.
