# Project structured rich link text through original Android types

Type: feature
Status: ready-for-agent
Work state: open
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
