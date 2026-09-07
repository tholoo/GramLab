# Match quoted code/pre validation in the GPL adapter

Type: bug
Status: ready-for-agent
Work state: resolved
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

## Worker result

Patch 0014 changes only `GramLabBridge.entities`. Equal-offset/equal-length quotes sort before
other entities while equal nonquotes retain stable input order. Validation now inspects every
active ancestor: code/pre accepts quote ancestors only, and no entity may have a code/pre ancestor.
Existing range, crossing, nested-quote, type, payload and UTF-16 boundary checks remain in place.

A fresh pinned 14-patch export applies without fuzz. Compared with the retained exact 13-patch
source, only `GramLabBridge.java` differs under `TMessagesProj/src`. All 1,471 original UI Java
files and 5,195 original resource files match acquired upstream byte-for-byte, and the source lock
and dependency-verification metadata are unchanged. This is preparation/source evidence only;
the coordinator still owns compilation, old/new codec behavior and real Android acceptance.


## Combined integration acceptance

The corrected normal16 inventory passes all 45 distinct Android cases: two focused rich-link
cases in 135.98 seconds plus the remaining 43 in 2525.72 seconds. The coordinator independently
verifies exact collection coverage with no duplicate or missing cases, unchanged source/fixtures,
APK and runtime profiles, and the primary checkout import. This is resumed coverage on one
immutable APK, not one uninterrupted run. No earlier contaminated result is reused.

The 447-case core gate passes at 81.18% coverage, and applicable static/workflow checks pass.
Fresh quoted-code edit/restart and list restart PNGs were inspected alongside the already reviewed
rich-link originals and reports. Original missing-field, disk-space, late-launch and import
failures remain retained; passing this gate does not establish their broader causes as fixed.
The assigned feature/fix is integrated and accepted. Media, mentions, automatic rich detection,
custom emoji and the full operational milestone remain unfinished.
