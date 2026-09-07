# Project explicit user mentions through the original native codec

Type: feature
Status: ready-for-agent
Work state: open
Blocked by: none for authored fixtures; 50 for real-bot integration

Own this ticket, new `clients/android/patches/0022-rich-text-mentions.patch`,
`tests/probes/android_rich_mentions_codec.py` and `tests/test_android_rich_mentions_codec.py`.
Coordinator owns series/README, shared docs, prepared source, builds and all guest execution.
Keep changes inside GramLabRichMessage, GramLabBridge and BridgeProbe in the GPL adapter/probe;
request ownership expansion if an actual dependency requires it. Preserve original renderer,
resources, input handlers, existing rich/link/media semantics and legacy bridge behavior.

Follow the approved mention proposal and frozen mentions-implementation-contract.md. Project
canonical ID-only mentions into original recursive TL_iv.textMentionName and observe the exact
64-bit ID after actual native serialization. Admit/validate newly disclosed authoritative User
records before dependent snapshot/change/callback messages can be applied. Duplicates, malformed
users, conflicting cached fields, invalid/missing mention IDs and missing identity dependencies
must reject explicitly. Preserve the current exact synthetic User fields and no profile mutation.

Use a per-decode identity context or equivalent existing World-bound snapshot state; do not add
an unscoped mutable global identity registry. Validate complete response dependencies and content
before installing newly disclosed identities into persistent/runtime controller state. Ensure
original native update/controller delivery receives users before their messages, including on
first delivery, replay and cold restart. Discuss internal ordering risks with coordinator early.

Independently author complete valid and malformed v3 snapshot codec fixtures covering recursive
Persian/English labels, empty labels, repeated/third-party identities, 64-bit IDs, and legacy
rejection. Retain existing native full-output comparisons; do not derive expected JSON from the
new mapper. This codec worker does not replace real-bot/live-update/restart acceptance.

Read AGENTS, TESTING, licensing/upstream and parallel-work. Use the coordinator's reviewed normal21
prepared source read-only; produce the new patch in worker-owned ignored scratch. Verify exact
zero-fuzz application and reconstruct only the owned source files. Run scoped Ruff/format/mypy
and fixture collection, but no APK or guest. Send a frozen clean commit, exact field mappings,
provenance, checks and remaining behavioral acceptance. Keep this ticket claimed until integrated
native acceptance passes. No remote publication, external runtime traffic or account/DC access.
