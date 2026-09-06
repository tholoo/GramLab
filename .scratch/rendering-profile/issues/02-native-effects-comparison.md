# Observe native effects gates and compare original rendering

Type: task
Status: ready-for-agent
Work state: claimed
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
