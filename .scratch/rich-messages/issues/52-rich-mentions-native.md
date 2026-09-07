# Project explicit user mentions through the original native codec

Type: feature
Status: ready-for-agent
Work state: claimed by rich-mentions-native worker
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

Coordinator authorizes one bounded GramLabRuntime callsite change in patch 0022: pass its current
Snapshot into a Bridge connect overload for World/persona-bound immutable identity consistency
across reconnects. No other Runtime behavior is owned by this worker.

## Worker handoff (source and fixture verification only)

Task branch `task/rich-mentions-native`, assigned base
`4f21e06a0bc729c2567ffb9612561b8e7f5811ad`. The worker owns only this ticket,
`0022-rich-text-mentions.patch` and the two mention codec Python files. The coordinator-approved
Runtime expansion is exactly `GramLabRuntime.java:323`, changing its reconnect call to
`GramLabBridge.connect(configuration, snapshot)`. Series/manifest/shared docs are coordinator-owned.

The append-only GPL patch changes four source files. `GramLabRichMessage` uses one private decoder
instance and copied identity-ID set per decode. Canonical `text_mention` becomes original
`TL_iv.textMentionName`, with recursive `text` and exact long `user_id`; legacy decoding rejects
mentions explicitly. All existing renderer/resource/input files remain outside this patch.

`GramLabBridge` stages response-local User records with exact required/optional field types,
sorted v3 IDs, duplicate rejection and complete supported-profile conflict comparison. A private
synchronized immutable-profile fingerprint map follows only a World/persona-bound Snapshot
lineage, including concurrent polling/reconnect; it is revalidated and merged only after the
whole response decodes. Missing current dependencies cannot be replaced by old knowledge. Old
knowledge can persist privately after a later snapshot omits an identity. New response/history
users come from that response, not from the retained map. V3 histories include response users;
Change/EventBatch share an immutable captured batch list and copy its vector into original
TL_updates/getDifference envelopes. No users are sent to a controller during staging. Existing
media asset installation behavior is unchanged; this patch's atomicity guarantee concerns users.
Callback records require their answer field before identity publication (null remains pending).

`BridgeProbe` keeps its original default successful output. Optional mention test modes observe
`history_users: [{peer_id, user_ids}]`; mentions emit `{type, text, user_id}` after original native
TL serialization/deserialization. Reconnect/reconnect-twice/reconnect-recovery use the public
connect overload, and recovery reports `rejected_reconnect`. Changes report `{cursor, head, now,
envelopes:[{seq,date,users,updates}]}`; difference reports `{kind,users,updates,pts,seq,date}`.
Each observed update includes `{kind,pts,pts_count,message}`. Native users retain the existing
`{id,first_name,self,bot,username,language_code,phone}` observation. Callback mode serializes the
original answer and observes `{text,show_alert,cache_time}`. These modes invoke real bridge entry
points and original TL codecs, without reflection, a renderer or controller mock callbacks.
Malformed JSON structure is reported as `GRAMLAB_BRIDGE_INVALID_DATA` by the diagnostic probe.

There are 75 independently authored native cases (12 positive, 63 rejection), including exact
IDs above 2^53 and at 2^63-1, recursive mixed Persian/English/emoji labels, empty labels/credit,
self/recipient/third-party/repeated mentions, nested blocks/link labels, strict malformed IDs and
profiles, duplicate/missing/conflicting users, new/removed identity reconnect, remembered profile
conflicts after removal, wrong World/persona binding, rejected-response recovery, first change
and difference disclosure, truncated/edit envelopes, frozen callback dependencies and v2/v1
mention rejection. Expected JSON is authored independently of production projection helpers.
The host fixture speaks only the existing controlled loopback bridge routes with a fake test
capability. This fixture set supplements, rather than replaces, real-bot/native UI acceptance.

Verified in the assigned checkout:

- `tools/worktree check rich-mentions-native`; assigned base is an ancestor of HEAD.
- `tools/dev default --command uv sync --locked`; editable `gramlab.__file__` resolves inside
  this worktree when using `uv run --locked python` (plain Nix-shell Python is not the venv).
- Scoped `uv run --locked ruff check`, `ruff format --check`, and `mypy` for both new Python
  files pass through this checkout's `tools/dev default --command`.
- `tools/dev default --command uv run --locked pytest --collect-only tests/test_android_rich_mentions_codec.py`
  collects one Android test. Fixture construction confirms 75 distinct names and complete oracles.
- `patch --batch --fuzz=0 -p1` applies to all four private preimages with no offsets or fuzz;
  reconstructed files match all four private edited files byte for byte. `git diff --check` passes.

Source provenance: preimages were copied read-only from the coordinator's normal21 prepared
source `.cache/android-build/offline/source`; only worker-owned
`.cache/mentions-native/{base,modified,verify}` copies were used. Full acquired upstream and the
shared prepared tree were not modified. Private verification evidence is retained in
`.cache/mentions-native/zero-fuzz-apply.log` and `.cache/mentions-native/source-provenance.json`.
Preimage SHA-256 values (under the standard org/telegram/gramlab source package):

- GramLabBridge.java: `bc95cece871da75cf86947a06a2e5d8502ce3573b5096eff45add50457f5739f`
- GramLabRichMessage.java: `e68a55d445d6d43b92ffb2851024bcc5fad8f82015742ba9d1bfd59d078bbf01`
- GramLabRuntime.java: `f8b9c961ef181088cc71015d76a6de614b80b90f32ee73a7fa327d79640c7af5`
- TMessagesProj_GramLab BridgeProbe.java: `fdbc6cdf354197cccabaf0050a877a87b8d4198f228f5e8c4beb836fb276894b`

No APK compilation, guest run, network/DC test or native rendering assertion was performed by
this worker. Coordinator acceptance must add the series entry, independently review source and
publication ordering, build the combined source, execute this full native codec matrix plus
existing rich/media regressions, and prove original rendering/live edits/replay/cold restart with
real bot scenarios. Keep this ticket claimed until those gates pass. No task-owned processes or
runtime locks remain after handoff; the branch is frozen for coordinator integration.
