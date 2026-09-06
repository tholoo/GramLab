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
