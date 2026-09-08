# Avoid repeated storage of identical archived APKs

Type: task
Status: ready-for-agent
Work state: implemented on `task/immutable-apk-artifact-storage`; coordinator review pending
Blocked by: coordinator review and integration

Own this ticket, `tools/artifact-store`, `tests/test_artifact_store.py` and
`docs/development/artifact-storage.md`. Coordinator owns shared contributor/CI changes and all
actual archived-artifact mutation. No native, core runtime, dependency or agent-guidance edits.

Retained completed guest runs repeatedly copy identical large APKs. A coordinator-only verified
archive compaction demonstrated substantial reclaimed storage while preserving every original
artifact path and byte. Generalize that bounded operation into reusable developer tooling so
disk capacity does not repeatedly interrupt native work. Keep all host paths and measured local
inventory in ignored plans/receipts, not this repository's public files.

Provide explicit plan and apply commands for regular `.apk` files under a caller-supplied archive
root and a separate content store. Plan records exact SHA-256, size and source identity/metadata;
apply validates the whole plan before mutation and rechecks each source before replacement. Only
byte-identical groups share storage. Copy and verify the content object before replacing any
original path with a hardlink; use atomic replacement, read-only shared objects and durable
receipts. Retain original permissions/timestamps in receipts. Never remove an artifact path,
change its content, follow symlinks, cross the declared root, touch guest disks or select a live
run implicitly. Reject stale/changed inputs and collisions. Interrupted application must leave
every artifact readable and preserve enough receipt information to finish or diagnose it safely.

Document the explicit completed/quiescent archive precondition, shared-inode/read-only semantics,
and how to materialize an independent writable copy from retained bytes and original metadata.
Do not deduplicate mutable build outputs or active run staging. Preserve existing CLI output/exit
conventions and use only the standard library. Scope the implementation to this archival use;
do not introduce a general filesystem cleanup framework or automatic deletion policy.

Use real small filesystem fixtures for complete byte/path preservation, duplicates versus unique
data, stale plans, symlink/path escape, preexisting collisions and interruption before/after atomic
replacement. Run focused tests, strict typing and lint/format; no guest, build or full core gate.
Return a clean frozen branch and structured handoff. Production artifact mutation remains with
the coordinator after code review; the earlier one-off result is not this tool's acceptance.

## Worker evidence

`tools/artifact-store` provides explicit create-only `plan` and confirmed-quiescent `apply`
commands. Plans bind canonical archive/store roots to sorted regular APK paths, SHA-256 values,
sizes and source metadata. Apply validates the entire inventory and all existing objects before
mutation, copies and verifies distinct content, publishes mode-0444 objects without overwriting,
then revalidates each source through directory-file-descriptor anchored paths before atomic
hardlink replacement. Plans and complete receipts are bounded to 16 MiB before mutation; manifest
reads are descriptor-bounded. Fsynced receipts retain original metadata and recover both published
objects and replacements interrupted before their journal entries.

Seventeen real temporary-filesystem cases pass under the outer loopback-only namespace, covering
duplicate and unique bytes, complete path preservation, idempotence, byte/mode/inode staleness,
symlink, path escape and unmanaged-hardlink rejection, parent substitution before and during
apply, content and create-only output collisions, quiescence confirmation, manifest/receipt bounds,
and interruptions before/after replacement and after object publication. Retained JUnit is
`artifacts/immutable-apk-artifact-storage.xml`. Scoped Ruff lint/format, strict mypy, bytecode
compilation and assigned-checkout import verification pass. No actual archive, guest, build,
runtime/core API or shared configuration was changed.
