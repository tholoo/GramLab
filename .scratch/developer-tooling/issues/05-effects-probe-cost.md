# Reduce redundant native effects observations

Type: task
Status: ready-for-agent
Work state: resolved after coordinator integration
Blocked by: none

Worker owns tests/probes/android_effects.py and this ticket only. Coordinator owns the host test,
shared docs, runtime defaults, integration and builds. The passing four-state effects probe takes
174–176 seconds and is the longest case in the current native gate. Settings helpers repeatedly
capture the same UI without an intervening input; reuse an already-observed tree and its target
bounds while that state is current. Do not introduce a cross-input stale cache.

Preserve baseline/blur/glass/restored original PNG/XML, complete history, checkbox/pref/battery/
account assertions, cold launches, notification-sheet handling, unsent wrapping draft trigger,
original shader breakpoint evidence and cleanup. Retain original observations before input and
after each state-changing input. Keep explicit failure on missing/ambiguous/unchanged controls;
do not reduce verification to preferences or replace UI input. No tap retries, timeouts, settings,
graphics profile, renderer, APK, class-loading or runtime network changes are assigned.

Before editing, count current observation calls along the real settings path and retain baseline
timings from the existing passed focused and full-gate JUnit artifacts. After a bounded change,
run focused static checks and the single effects host test with the same approved read-only APK,
under android-gate and the outer network guard. Coordinate lock availability with root; no full
gate, guest sharing, APK build or new upstream/dependency acquisition. Compare actual elapsed time
and retained navigation capture count while inspecting all four original phase images and full
semantic assertions. Report uncertainty if the measured run does not improve; fewer calls alone
is not a measured speedup. Use the real probe, not a synthetic stopwatch test.

Commit only owned changes and return a frozen clean branch with exact verification, timing and
artifact evidence. Keep the ticket claimed for coordinator acceptance. This optimization does
not change the broader product fidelity target or turn an uncontrolled run into a benchmark.

## Comments

- Claimed on `task/effects-probe-cost` at base
  `c6d30587d67c400b7151585c0728ef4df361544c`. The worker owns only this ticket and
  `tests/probes/android_effects.py`. Acceptance retains every phase and semantic assertion while
  reusing a UI tree only until the next input invalidates it.

## Answer

The settings helpers now pass the current observed tree and its validated target bounds through
lookups until an input invalidates that state. Every launch, notification dismissal, swipe and tap
still has a following observation, and missing, ambiguous or unchanged controls still fail.

The retained focused baseline recorded 174.300 seconds for the test call and 174.43 seconds for
the suite; the integrated gate recorded 175.800 seconds for the same case. The focused guarded run
after this change passed in 159.03 seconds (158.889-second call) with the same pinned APK digest.
Navigation evidence fell from 39 captures (38 settings plus one shader precondition) to 20 (19
settings plus the shader precondition). Differing host load makes the lower elapsed time an
observation, not a controlled speedup claim.

Ruff lint/format and strict mypy passed. The actual host test retained all four original PNG/XML
phases, complete equal history, cold launches, checked-state and preference transitions, battery,
account and guest-isolation evidence, the wrapping unsent draft, and the original main-thread
`LiquidGlassEffect.update` breakpoint. Visual review found the expected opaque baseline,
translucent blur, glass variation and opaque restoration with complete bilingual content. No APK,
renderer, defaults, timeout, retry or runtime-network behavior changed.

The list-inclusive combined Android gate passes all 38 cases without skips. Its effects case
passes in 132.683 seconds with the integrated list-capable APK, all four original phases, original
shader evidence and 20 navigation captures. The coordinator reviewed all four new phase images.
The preceding effects case took 175.800 seconds; this is an observed difference under uncontrolled
load, not a causal benchmark. The bounded observation reduction is accepted.
