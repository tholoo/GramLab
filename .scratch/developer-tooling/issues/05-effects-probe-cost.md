# Reduce redundant native effects observations

Type: task
Status: ready-for-agent
Work state: open
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
