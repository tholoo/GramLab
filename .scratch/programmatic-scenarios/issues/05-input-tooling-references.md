# Resolve arbitrary Unicode Android input tooling

Type: research
Status: ready-for-agent
Work state: resolved
Blocked by: none

Own only this ticket and docs/development/android-input-tooling-references.md. Inspect pinned
Android/AOSP/SDK input and accessibility contracts for an independent app_process shell helper
that enters Unicode text into the original composer and clicks Send. Resolve connection,
permissions, lifecycle and safe request framing. Static inspection only; no acquisitions,
client/guest launches, UI modifications or claims of runtime success. Root owns implementation.

Findings: [Unicode input tooling references](../../../docs/development/android-input-tooling-references.md).
Verified platform-36 public SDK signatures with javap and inspected immutable Android16 AOSP
connection, permission, lifecycle, input and accessibility sources. Identified reflective shell
setup, main-looper preparation, single-registration serialization and safe stdin framing.
Guest availability and full Unicode/send behavior remain unverified and owned by root.
Validation: local links, source revision references, public-tree privacy and `git diff --check`.
