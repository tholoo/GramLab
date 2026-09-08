# Share immutable media bytes without changing existing identities

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

Prepare the approved World-owned file support by separating immutable bytes from existing
photo/custom-emoji metadata. This is an internal persistence migration, not document API support.
Preserve every public World and bridge v3/v4 result, file ID, grant and image admission rule.
Do not implement document methods, bridge v5, MIME/filename policy, albums or native changes here.

## Ownership and contract

Own this ticket, `src/gramlab/world.py`, `tests/test_media_world.py`, and new
`tests/test_media_storage_migration.py` plus a bounded legacy fixture under
`tests/fixtures/media_storage_v7/`. Coordinator owns shared docs, CI and integration.

Schema 8 introduces `media_blobs(sha256 TEXT PRIMARY KEY, body BLOB NOT NULL)`.
Existing `assets` keeps its exact IDs and metadata columns but moves body into media_blobs,
with its existing unique sha256 referencing the blob. Other tables and identities stay unchanged.
Fresh creation and migration must produce the same schema. Byte lookup joins the blob through
existing typed assets and grants; knowing a hash must not authorize access. A private byte-storage
helper may prepare future document reuse, but must remain in the caller's write transaction and
must not commit independently. Avoid speculative abstractions or new public methods.

Migration from populated schema 7 must be atomic, preserve all rows and foreign-key targets,
and serialize concurrent openers. Disable foreign keys on the fresh connection before the
migration transaction only if needed for the table replacement; acquire BEGIN IMMEDIATE and
recheck version after acquiring the lock. Copy immutable bytes, replace assets without renaming
the old table first (which could rewrite child FK targets), check FK integrity, and update
user_version last. Restore FK enforcement before returning. Any injected interruption must roll
back completely. Existing supported legacy versions still migrate to current; future versions
must remain rejected. No executescript inside an intended atomic migration transaction.

## Acceptance

Create and retain an independently populated schema-7 fixture using the unmodified assignment
base, with photos, emoji, bot file reuse, grants, edits, callback/revision data and messages.
Record portable provenance and literal expected identities/output. Do not manufacture the legacy
fixture by downgrading the implementation under test. Compare complete public outputs, downloaded
bytes, histories/events, callback retry and persona authorization before/after/reopen. Prove
concurrent migration and rollback/retry, not merely table presence or version equality. Preserve
existing deduplication, denied access and failed-publication atomicity; no ID consumption on failure.
Check real schema/FK integrity and exact byte retention, including shared photo/emoji assets.
Update the existing schema-5 fixture construction honestly for the new current schema.

Follow TESTING.md. Run focused media/migration/custom-emoji World tests and scoped Ruff/strict
mypy in the checkout's pinned offline environment. No Android guest, build, full gate or network
assigned. Preserve red/green evidence, keep generated storage bounded, and return a clean frozen
commit with exact checks, pending evidence and terminal process state. The coordinator reviews,
merges, runs combined checks and updates shared documentation.
