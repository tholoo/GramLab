# Project structured rich link text through original Android types

Type: feature
Status: ready-for-agent
Work state: integrated and compiled; native acceptance pending
Blocked by: none; canonical shared contract frozen

Follow [the contract](../../../docs/development/rich-links-contract.md). Native worker owns only
`clients/android/patches/0015-rich-link-text.patch`, patch `series`, and this ticket on
`task/rich-links-native`. Coordinator owns probes, fixtures, shared docs, builds and guests.

Append the three native projections and independent reverse serialization to the GPL rich
adapter/probe. Preserve recursive labels and exact canonical metadata, reject missing/wrong/extra
fields and unknown types, and use the original URL/email/phone classes. URL cached webpage ID is
zero. Keep normal source free of experimental geometry; no renderer/controller/resource or
network behavior change is assigned.

Avoid duplicating a complete upstream export for routine editing. Copy only the adapter source
files from the coordinator's verified read-only fourteen-patch export into task-local ignored
storage, edit those private copies, and generate an append-only patch. Verify zero-fuzz dry-run
against that exact preimage and inspect the resulting adapter changes. Coordinator owns the full
integrated source comparison and build, so report this honestly as source-only validation rather
than fresh full preparation, compilation or runtime proof. Do not mutate the shared export.

Use the assigned worktree/branch; commit only owned files and return the exact preimage proof,
patch check and frozen clean branch with terminal resources. Leave ticket claimed until combined
acceptance. Report an unexpected required UI/network change before expanding ownership.

## Worker evidence

The append-only patch projects `url`, `email_address`, and `phone_number` nodes recursively into
the pinned client's original `textUrl`, `textEmail`, and `textPhone` classes. Each decoder branch
admits only its canonical fields, requires string metadata, and gives URL values a zero cached
webpage ID. The independent probe reconstructs those exact metadata keys and rejects a nonzero URL
webpage ID.

The verified fourteen-patch preimages have SHA-256
`1b8e5ec6c6a97fdbbcc6fdca2a3f493f43f8a6f64d91ae40e705b5bd731511fd` for
`GramLabRichMessage.java` and
`5ce379226b7a319131f9845b8de711be7e786d3931fc4e24a1b28b8195af961f` for
`BridgeProbe.java`. Private ignored copies compare byte-for-byte with those shared read-only files.
`patch --dry-run --fuzz=0 -p1` applies both patch sections cleanly to that exact source. This is
source-only validation; full prepared-source comparison, compilation, adversarial codec checks,
and native rendering remain coordinator-owned.

Coordinator preparation compares all 43,268 normal14 reference files before and after zero-fuzz,
zero-offset patch application. Only the two owned adapters change; independently patched private
copies match their resulting digests. Original renderer/resources and strict dependency metadata
are preserved. The incremental offline normal15 build passes in 2 minutes 48 seconds (78 tasks,
11 executed), source digests remain unchanged and the immutable APK passes signature verification.
With verified primary imports, normal14 first passes its baseline and then rejects the valid
rich-link scene in 60.26 seconds. Normal15 codec/rendering and combined native acceptance remain.
