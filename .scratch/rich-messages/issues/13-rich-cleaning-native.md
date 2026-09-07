# Verify cleaned rich content through a real bot and original Android

Type: task
Status: ready-for-agent
Work state: assigned; awaiting worker claim
Blocked by: coordinator integration of ticket 12 for positive execution

Worker owns new tests/test_rich_cleaning_round_trip.py, tests/test_android_rich_cleaning.py,
tests/probes/android_rich_cleaning.py and this ticket. The coordinator owns integration, shared
probes, static-check configuration, docs and all Android execution. Use a separate worktree.

The [cleaning contract](../../../docs/development/rich-text-cleaning.md) is fixed; the Python
implementation on ticket 12 is reviewed and frozen separately. Prepare a small independently
authored dirty-input and canonical-output scene. Reuse the real standard-library HTTP fixture bot,
stage_rich_scenario and rich_round_trip flow, and the existing native probe's scene_checks seam.
Keep setup/expected assertions shared between the simulation and native host tests where useful.
Do not modify shared probes or copy client-derived code into these Python files.

Initial and edited messages must expose the canonicalization difference through complete real Bot
API replies and durable history, then through actual native serialization. Cover accepted tab,
Unicode removals, a direction-marker run, preformatted language and unchanged Persian/ZWNJ text.
Use short visible strings for the original 320 x 640 profile; long truncation boundaries belong
to the core contract tests. Retain raw input separately from expected canonical output. Switch the
edit to RTL and verify the live view and cold restart with original PNG/XML. Expected content
must not be computed using the validator, codec or source input transformation code.

The simulation case should demonstrate missing normalization on this base via the real bot and
complete output. The native case should compare the same complete canonical semantics and retain
normal guest isolation/accounts, launch status, applied-edit trace and report evidence. Reuse the
existing APK: no Java change or build is needed for world-side normalization. No input fallback,
runtime egress, renderer/profile change or new capture API is assigned.

Run focused simulation red and scoped lint/format/mypy under the pinned offline environment and
outer network guard. Positive simulation and native execution depend on the coordinator merging
the frozen core fix; report this honestly rather than weakening expected output. The worker must
not launch guests or build an APK. Commit only owned files and hand back a frozen clean branch;
keep the ticket claimed until coordinator integration and acceptance.
