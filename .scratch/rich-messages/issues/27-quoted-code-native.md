# Match quoted code/pre validation in the GPL adapter

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: none for patch implementation; coordinator owns integrated native acceptance

Follow [the frozen core/native contract](../../../docs/development/quoted-code-formatting.md) and
the parallel, licensing and upstream workflows. Own only this ticket,
`clients/android/patches/0014-quoted-code-entities.patch` and `clients/android/patches/series`,
on `task/quoted-code-native`. Coordinator owns patch README, shared docs and all Python probes.

Append a narrow GPL patch changing only `GramLabBridge.entities` validation/order. Preserve
original UI/controllers/resources, the nine types and payload fields, all unrelated validation
and transport behavior. Handle quote-first equal extents and all active ancestors as specified.
Do not rewrite an earlier patch or include experimental geometry in the normal series.

Prepare fresh pinned source using the locally resolved acquired checkout and verify zero-fuzz
application, preserved original renderer/resources and unchanged dependency metadata. Inspect
the changed source against the base export. No APK/guest run is assigned: coordinator uses the
existing build cache for one integrated build and owns old/new native codec and real-bot checks.
Report preparation evidence honestly as source evidence, not compilation/runtime acceptance.
Commit only assigned files, return a frozen clean branch with terminal processes, and leave the
ticket claimed until coordinator acceptance. Request any ownership changes before editing.
