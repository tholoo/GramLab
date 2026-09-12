# Implement atomic album core and bridge v6

Type: task
Status: ready-for-agent
Work state: claimed
Owner: album-core-v6
Blocked by: none

After the album contract is frozen, implement strict `sendMediaGroup`, schema-10 group/counter/member
storage, one private final-message atomic World publisher, ordered messages/events and complete-group
bridge-v6 delivery. Own `src/gramlab/world.py`, `src/gramlab/bot_api.py`,
`src/gramlab/client_bridge.py`, `tests/test_media_groups_world.py`,
`tests/test_media_groups_http.py`, `tests/test_media_groups_bridge.py`,
`tests/test_album_storage_migration.py` and `tests/fixtures/album_storage_v9/**`. Do not call the
standalone public send methods per member or parallelize another worker that edits these files.

Preserve exact v1–v5 contracts and reject grouped state there before cursor/action mutation. Verify
populated schema9 migration/reopen and foreign keys, concurrent opens/sends, complete rollback at
early and injected late failures, deterministic retry, exact per-item/logical/physical aggregate
boundaries, repeated upload references, JSON/form/multipart parsing, group-aware `limit=1`, boundary
and `limit=1000` pages, exact HTTP409 `resnapshot_required`, response-kind dependency rules and
strict malformed-group failures. Encode the approved grouped-edit branch: either both edit methods
reject with full-state equality, or caption/same-kind edits preserve ID/ordinal/membership and v6
validates their single-row lineage. No APK, guest or public acceptance belongs to this ticket.

## Worker implementation evidence

Implementation is complete on `task/album-core-v6` and remains claimed pending coordinator review
and integration. The coordinator granted narrow additional ownership of
`tests/test_world_creation.py`, `tests/test_media_storage_migration.py`,
`tests/test_document_storage_migration.py`, and `tests/test_media_world.py` solely for the mechanical
schema-9-to-10 final-version/table inventory and future-10-to-11 expectation updates.

The meaningful red case failed because `World.send_media_group` did not exist. The implemented
schema-10 publisher validates and resolves a whole homogeneous 2–10-member photo/document group,
allocates one World-wide rollback-safe signed-64-bit group ID, and publishes final canonical
messages, membership, events, revisions and grants in one writer transaction. Repeated attachments
are counted once physically and once per occurrence logically; album documents always bypass the
standalone default classifier. Both grouped edit methods reject with full database equality.

Bridge v6 carries canonical `media_group_id`, validates persisted membership/topology, expands a
trailing creation group by at most nine rows, rejects every inside-group cursor with exact HTTP 409
`resnapshot_required`, and preserves v1–v5 rejection before callback mutation. V6 snapshots,
changes, messages, callbacks, assets, documents and custom-emoji-document routes retain v5's
dependency topology. The pinned, token-free `tests/fixtures/album_storage_v9/world.sql` proves
populated migration, concurrent opening, interruption rollback, reopen and foreign-key integrity.

Retained green evidence:

- `artifacts/album-core-v6-world-01.xml`: 114 World/migration/media/document cases.
- `artifacts/album-core-v6-http-bridge-02.xml`: 37 isolated HTTP/bridge regressions after restoring
  strict v5 document-path rejection.
- `artifacts/album-core-v6-focused-world-02.xml`: 23 album World/migration cases, including exact
  100,000,000-byte logical and physical boundaries.
- `artifacts/album-core-v6-focused-http-bridge-03.xml`: 15 isolated album HTTP/bridge cases.
- `artifacts/album-core-v6-non-android-01.xml`: all 1,340 non-Android tests passed in 109.06 seconds
  inside a loopback-only network namespace.
- Strict mypy, Ruff lint and Ruff formatting pass for all 11 changed Python files.

No Android guest, APK build, external network, publication or unowned production file was used.
