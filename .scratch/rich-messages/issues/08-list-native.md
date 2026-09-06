# Project structured lists through the original Android renderer

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

## Ownership and interface

Android worker owns clients/android/patches/0012-rich-list-projection.patch (new),
clients/android/patches/series, clients/android/fixtures/rich-message-invalid-lists.json (new),
tests/probes/android_rich_lists.py (new), tests/test_android_rich_lists.py (new) and this ticket.
The coordinator owns the shared canonical fixture, core implementation, public examples/walkers,
global docs, patch README, build environment, builds and integration. Preserve patch0011 unchanged.

Use [the pinned contract](../../../docs/development/rich-list-references.md) and the committed
canonical catalog clients/android/fixtures/rich-message-lists.json. Extend only the semantic
adapter and BridgeProbe inside the GPL patch. Decode canonical list blocks to native unordered or
ordered containers with block items, recursively preserving blocks, flags, numbers, values and
label type. Empty item blocks survive serialization and are skipped by the original renderer.
Set native optional flags exactly; verify the original serializer/deserializer retains values.
Unknown/inconsistent canonical fields, labels, types, ordering, scalars, ranges and resource
overflow reject before native state. Keep top-level and non-list existing boundaries unchanged.

Native output consumes required canonical labels; these are output-only and must not be admitted
as Python public input. Do not reconstruct a flattened text rendering or modify original layouts,
UI resources, fonts, classes, presets or entitlement flags. Incoming bot checkbox state comes from
bot send/edit; native user editing is not authorized by that fact. The original editability gate
must remain effective.

## Parallel verification ownership

Prepare an independent native codec probe using the shared canonical catalog at the bridge
snapshot boundary. The Python list validator is another worker's unfinished dependency; do not
merge that worker or bypass it in production. A trusted fixture snapshot may exercise the codec
independently, but is not real-bot/rendering evidence. Reuse the existing adapter/probe conventions.

Write the missing-list native test before changing the patch. Run a focused red on the approved
read-only old APK only after the coordinator releases android-gate. Inspect the actual unknown-list
failure, not a startup/infrastructure error. Preserve complete native codec expectations and a
malformed-snapshot corpus. Guard missing profile/APK/KVM consistently with existing marked tests.

The coordinator owns the incremental APK build and post-merge positive native checks, so this
worker must not create a clean duplicate build or run a full gate. After the valid red, implement
the patch and run fresh preparation/applicability plus source/resource identity checks and focused
Python static checks where available. Return a frozen patch/probe branch with compiled/positive
native coverage explicitly pending; that limitation is part of the assigned verification split.

After integration, the coordinator must verify the full canonical catalog through actual native
serialization, malformed rejection, and a real bot send/live edit/cold restart in original PNG/XML.
Rendering acceptance includes nested markers, wrapping, all label styles, RTL/LTR indentation,
checked/unchecked incoming bot rows, invisible empty block items and a user tap that cannot mutate
the bot-owned checkbox. Public capture/inline traversal is a separate integration requirement.
Do not claim list support complete from codec or source evidence alone.
