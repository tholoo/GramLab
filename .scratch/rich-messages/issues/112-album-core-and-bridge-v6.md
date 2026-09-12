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
