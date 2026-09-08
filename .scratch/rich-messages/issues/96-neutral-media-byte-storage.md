# Share immutable media bytes without changing existing identities

Type: task
Status: ready-for-agent
Work state: claimed by neutral-media-byte-storage; implementation complete, awaiting coordinator review
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


## Worker handoff

Implemented schema 8 with shared immutable `media_blobs`, preserving typed asset metadata and
all existing IDs, grants and public methods. Fresh creation and migrated schemas match. The v7
replacement runs under `BEGIN IMMEDIATE`, rechecks the version, preserves child FK targets,
checks integrity and updates the version last. Failed publication rolls back bytes and IDs.
The original v5 synthetic fixture now explicitly removes all post-v5 tables, including blobs.

The retained populated v7 fixture was produced with untouched assignment-base source before
implementation. Its complete public outputs were independently rechecked afterward using that
same base export, including reopen and unchanged database rows. Portable provenance, source/input
hashes, output hashes and manual reproduction are in `tests/fixtures/media_storage_v7/README.md`.
No upstream acquisition, native build, guest, full gate or external network was used.

Validation uses this checkout's pinned offline shell and private virtualenv. The new migration
suite initially produced nine expected failures and one pass against unchanged schema 7; its
complete legacy public-output comparisons already passed before the schema assertion failed.
The first implementation run passed 24 focused tests. An added test initially used a non-emoji
entity range; correcting its input preserved the existing admission rule. The subsequent bounded
selection passed 44 tests, with one legacy HTTP check failing because isolated loopback was down.
That exact check passed on retry with the documented `ip link set lo up` guard. Together these
cover all 45 selected tests on the final behavior (one unrelated HTTP test intentionally deselected):

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c '
  ip link set lo up
  .venv/bin/pytest tests/test_world.py tests/test_media_world.py \
    tests/test_media_storage_migration.py tests/test_custom_emoji_world.py \
    tests/test_custom_emoji_isolation.py \
    tests/test_client_bridge.py::test_previous_world_format_preserves_pending_delivery_when_adding_client_identity \
    tests/test_callbacks.py::test_concurrent_upgrade_preserves_world_identity_and_pending_bot_delivery \
    tests/test_update_delivery.py::test_negative_offset_counts_pending_rows_in_a_sparse_legacy_queue \
    tests/test_client_sends.py::test_concurrent_v4_upgrade_preserves_filters_and_backfills_persona_positions \
    -k "not document_http" --junitxml=artifacts/media-storage-focused.xml
'
```

Scoped Ruff lint/format and strict mypy pass for all four owned Python files:

```sh
tools/dev default --offline --command bash -eu -c '
  .venv/bin/ruff check src/gramlab/world.py tests/test_media_world.py \
    tests/test_media_storage_migration.py tests/fixtures/media_storage_v7/generate.py
  .venv/bin/ruff format --check src/gramlab/world.py tests/test_media_world.py \
    tests/test_media_storage_migration.py tests/fixtures/media_storage_v7/generate.py
  .venv/bin/mypy --strict src/gramlab/world.py tests/test_media_world.py \
    tests/test_media_storage_migration.py tests/fixtures/media_storage_v7/generate.py
'
```

Small JUnit red/intermediate/green reports and the independent base verification receipt remain in
ignored `artifacts/`. Disposable fixture databases and the temporary base source export are retired.
All worker commands are terminal. Coordinator owns review, combined verification, shared docs and
integration; keep this ticket claimed until those complete. Shared docs should record internal
schema 8 while retaining unchanged v3/v4 delivery and the existing image admission boundaries.
