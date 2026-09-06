# Observe native effects gates and compare original rendering

Type: task
Status: ready-for-agent
Work state: verified focused comparison; combined Android gate pending
Owner: coordinator
Blocked by: none

Coordinator owns focused effects probe/test files, this ticket and shared profile documentation.
Read docs/development/android-effects-profile.md. Use a fresh contained guest with the verified
APK and one synthetic world. Capture baseline settings/UI; exercise the original debug/performance
and Power Usage controls, retaining persisted mask, battery gate and cold-launch observations.
Compare baseline, blur and glass-enabled frames without changing original renderer code or default
runtime profile. Inspect actual pixels; a stored flag or lack of a crash is insufficient proof
of the shader path. Preserve unsupported or inaccessible surfaces explicitly.

Keep the guest under android-gate and coordinate with the rich-inline worker. Start with read-only
source/probe preparation and a narrowly scoped observation. No accounts, external runtime network,
new source acquisition or repeated full suite is authorized by this ticket. A proposed default
profile change remains subject to user consultation.

## Initial native observation

A contained guest now confirms the actual Power Usage rows: Low Power Mode off at 100% battery,
Blur and Liquid Glass both initially unchecked. Original UI toggles persist masks 198940 after
Blur and 461084 after both, with threshold10 and no performance override. Cold launch retains
the selected values, and the original composer becomes translucent. IPv4/IPv6 denial and zero
accounts remain observed. This first trial does not isolate blur from glass or prove shader entry.

The prepared follow-up uses one guest for baseline, blur, glass and restored captures, plus a
one-shot external debugger observation of the original LiquidGlassEffect.update method. No
renderer/source/profile change is needed. The private-debug class exception permits this more
controlled comparison without changing performance class. Measured class itself remains unobserved.

## Probe diagnosis

The first comparison captured baseline, blur and glass states, but the subsequent breakpoint
timed out: the empty composer was already focused, so another tap did not establish display-list
invalidation. Pinned source caches the drawable list. The revised trigger types an unsent wrapping
draft through original input; a second run reached the shader observation and visibly expanded
the field from 40 to 82 pixels before clearing it. That run later stopped at the original optional
notification sheet when reopening settings, before the restored phase. Neither run is a passing
comparison. Their failure evidence is preserved separately.

The revised probe retains each phase and the breakpoint independently, dismisses only an observed
notification sheet with Back, and keeps restoration in the same guest. Focused Ruff, format and
strict typing pass; the complete revised native comparison remains pending. No renderer changes,
new APK, runtime network permission or default-profile change were made.

## Focused acceptance

The revised complete comparison passes in 174 seconds. It verifies all four states, restored
checkboxes/mask, equal complete history, zero accounts, battery 100 and guest egress denial. The
original shader method is observed on the main thread with a nonopaque foreground color; the
wrapping draft is cleared without sending. All four original captures were reviewed. The report
loads its four original images without overflow or external resources at desktop/mobile widths.
The source-derived performance-class inference remains separate from observed runtime values;
restoring the two effect flags is not an identical-frame reset of system navigation/clock pixels.
The [effects profile](../../../docs/development/android-effects-profile.md) records these limits.
A later assertion/provenance-only update additionally checks the observed nonopaque alpha and
records the declared client pin and actual APK hash. The combined native gate will exercise that
final host-test version. No production or default-profile change belongs to this task.
