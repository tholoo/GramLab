# Preserve native rich-message projection

Type: task
Status: ready-for-agent
Work state: resolved
Owner: rich-android / task/rich-android

Claimed acceptance: implement strict native projection and serializer observations; export the
complete queue on a fresh tree. Coordinator owns APK build and Android runtime evidence.
Blocked by: none

Read ../spec.md. Own clients/android/patches/0011-rich-message-projection.patch (new),
clients/android/patches/series, clients/android/patches/README.md, dedicated codec fixtures/probes
under clients/android only if needed, and docs/development/android-rich-projection.md (new).
Own this ticket only among shared task records. Coordinator owns host/native runtime tests,
application build and integration, core/world/API files and shared compatibility/handoff records.

## Acceptance

- Inspect pinned TL_iv and RichMessageLayout and map the agreed official-shaped JSON rich_message
  to actual native objects, retaining plain messages and upstream rendering unmodified.
- Cover agreed text/heading/pre/footer/divider/quotation/table/details blocks, nested RichText and
  RTL. Reject unsupported/malformed input; never silently drop rich content or flatten into text.
- Mapping applies to snapshot, live updates and difference recovery paths that use shared decoding.
- Coordinate exact block/wrapper fields with core worker early. Report native mismatches.
- Export and verify the new patch on a fresh prepared tree, preserve upstream license and provenance.
  Send build/codec expectations to coordinator; avoid redundant full APK builds or Android gates.
- Commit only owned files and leave ticket claimed until integrated runtime verification.

## Worker handoff

Implemented patch 0011 with the native `TL_iv.RichMessage` projection and actual serializer
observations, a comprehensive canonical fixture and two independent table-boundary fixtures.
Strict accepted types, canonical optional fields and local resource bounds agree with the core
worker contract. Original renderer code remains unchanged. The first-row table width assumption
is documented as an explicit unsupported profile gap; it is not a Telegram API rejection claim.

The complete eleven-patch queue applies to a fresh pinned export; all three changed Java sources
compile against the pinned Android SDK and preceding verified client classes. All 6,667 compared
UI/resource/rich-layout files are unchanged. The canonical fixture agrees exactly with the core
contract, and both negative tables reject. Configuration/local links across 90 Markdown files and
`git diff --check` pass. These are source/type/contract checks; real guest serializer, rendered
screenshots, live edit and restart verification remain coordinator-owned and pending integration.

The branch remains claimed until that integration passes. The coordinator should build once from
the verified patch export and exercise both the visible scenario and full codec catalog, preserving
plain-message regression assertions. Shared handoff/compatibility records remain coordinator-owned.

## Coordinator integration checkpoint

Reviewed core and native changes pass the integrated real-bot contract. The full core gate passes
269 tests at 82.06% coverage. The new offline APK builds successfully; the focused native test
passes with complete codec catalog, explicit invalid-table rejection and visually inspected
send/edit/cold-restart captures. Shared documentation records the precise supported boundary.
The combined Android gate is still running; keep this ticket open until its required checks pass.

## Accepted integration

The integrated APK passes the full 29-test Android gate with no skipped tests in 1,630.71 seconds.
This includes the rich send/live-edit/restart and complete codec cases, existing plain formatting,
callbacks, composer input and controlled recovery boundaries. Core, static and package checks
recorded above pass. This closes this bounded ticket; broader rich surfaces and the full GramLab
feature inventory remain open. Generic public rich capture acceptance is tracked separately in 04.
