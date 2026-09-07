# Implement immutable World photos, Bot API uploads and bridge v3

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: none; approved shared contract frozen

Follow [the media contract](../../../docs/development/media-implementation-contract.md).
The worker owns `src/gramlab/world.py`, `bot_api.py`, `client_bridge.py`, `rich_messages.py`,
a new original `src/gramlab/media.py` if useful, `tests/test_media_world.py`,
`tests/test_media_http.py`, `tests/test_media_bridge.py`, and this ticket. Existing test files
may be read; report obsolete expectations to the coordinator. Shared docs, dependencies/locks,
runner/captures and Android source belong to the coordinator or other lanes.

Implement PNG and JPEG together, ordinary sendPhoto plus rich upload/edit/reuse, getFile/download,
atomic immutable storage and bot/persona grants, bounded multipart parsing and actual full decode.
Freeze no additional public interfaces independently: use the exact contract and report gaps.
Bridge v3 includes all retained grants on snapshot, exact replay dependencies, revisions and
versioned callbacks. Existing nonmedia APIs and persisted Worlds must remain compatible.

Prove pre-change rejection with public World/HTTP tests, then full structured success, migration,
restart, same-clock edits/no-ops, multipart boundary-like payloads and malformed/duplicate fields,
invalid/oversized/truncated images, cross-bot/World/persona access, old-grant lifetime and unchanged
state/IDs after failures. Cover v1/v2 media rejection before mutation/cursor advance and v3 errors.
Use independently authored expectations; do not call new internal helpers to construct expected data.

Run the new suites and relevant existing World/Bot API/client bridge/rich suites under the pinned
assigned shell and outer network guard; run scoped Ruff/format and source mypy. No guest or full
core gate is assigned. Use an isolated worktree/environment; commit owned files and send a frozen
clean branch, red/green evidence and terminal-resource handoff. Keep claimed until integration.

## Worker evidence

Implemented immutable SQLite PNG/JPEG assets, bot-scoped reusable file identities, persona grants,
ordinary and rich photo publication/editing, bounded multipart upload, `getFile`/authenticated file
download, and bridge v3 snapshots, changes, callbacks, assets and stored message revisions. The
pre-change dispatcher and rich validator rejected `sendPhoto`, multipart and photo blocks; the new
public boundary suites now cover both admitted formats, direct named file parts, rich upload/reuse,
caption normalization, restart, concurrent schema migration, rollback, isolation, old grants and
same-clock callback ABA revisions.

Guarded focused media tests pass 15 cases. The guarded combined media plus existing World, Bot API,
client bridge and rich-message selection passes 98 cases. Scoped Ruff format/check and strict mypy
pass on all owned source; no Android, guest or full core gate was run.
