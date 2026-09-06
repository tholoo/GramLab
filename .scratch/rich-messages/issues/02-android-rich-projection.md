# Preserve native rich-message projection

Type: task
Status: ready-for-agent
Work state: open
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
