# Implement the immutable custom-emoji catalog and public delivery

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: media validator ticket 57 for integrated codec acceptance

Own this ticket, `src/gramlab/world.py`, `src/gramlab/entities.py`,
`src/gramlab/rich_messages.py`, `src/gramlab/bot_api.py`, `src/gramlab/client_bridge.py`,
new `src/gramlab/_emoji_text.py`, and new `tests/test_custom_emoji_world.py`,
`tests/test_custom_emoji_api.py`, `tests/test_custom_emoji_bridge.py`,
`tests/test_custom_emoji_text.py`. The coordinator owns the BSL notice/provenance files; request
their addition before adapting the pinned predicate/table. Do not modify decoder, SDK/control,
runtime configuration, existing tests, native patches, shared docs or dependency locks.

Follow the entire [implementation contract](../../../docs/development/custom-emoji-implementation-contract.md)
for schema-7 migration, immutable/idempotent catalog, independent allocated/chosen logical IDs,
main/thumbnail asset reuse, transactional persona grants and all recursive entity carriers.
Implement complete Bot API lookup/download projection and v4 snapshot/change/callback/incoming/
document/asset delivery, plus explicit legacy rejection based on selected/frozen content. Preserve
all existing photo/mention contracts. No real entitlement, external downloads, silent omissions
or alternate renderer. Do not make registration append a new unsupported client event type.

Use independent complete expected HTTP/World/history/events/dependencies and public operations to
cover retries/conflicts/no-op/edit/reopen, two bots/personas/Worlds, chosen maximum then allocated
ID, unknown/mixed lookup, wrong identities, legacy frozen retries and unchanged state after
rejection. Incoming text tests include Persian/English, ZWJ, flags, skin tone and UTF-16 boundaries.
Use actual decoder from ticket 57 for final registered media acceptance; compile/implement the
stable interface while that dependency is in progress, but do not claim mocked media support.

Read AGENTS.md, handoff, TESTING, offline safety/licensing and parallel-work. Claim/check the
assigned worktree and verify imports through its tools/dev. Run focused tests in the outer
loopback-only guard and scoped Ruff/format/strict mypy. No full gate, APK build or guest.
Commit only owned files; send frozen clean tip/base, red/green evidence and missing dependency or
native acceptance honestly. Coordinator owns notice integration, merges and combined verification.

## Worker evidence

Implemented on `task/custom-emoji-core` from the assigned base. The pinned TDLib predicate,
schema-7 catalog, ordinary/rich admission, Bot API lookup/download, transactional publication
and v4 snapshot/change/callback/incoming/document/asset projections are covered by focused public
checks.

- Custom-emoji tests: 27 passed under the loopback-only namespace.
- Focused custom-emoji plus existing entity/rich/media/mention regressions: 141 passed in 35.413s;
  retained locally as `.scratch/custom-emoji-core-focused.xml` during review.
- Scoped Ruff and strict mypy: passed for all six owned production modules and four new tests.
- The focused regression selection excludes
  `test_schema_five_migration_is_atomic_across_concurrent_openers`; its expected schema `[6, 6]`
  is coordinator-confirmed stale after the required schema-7 migration.
- Registration checks used the coordinator-owned provisional copy of the corrected decoder at
  frozen decoder commit `6002108544f2fbb0bd772acf279078c9cf482059`. The decoder remains untracked
  and is not part of this worker commit.

Work state: ready for review

### Review follow-up

Fixed four independently reviewed gaps: v4 changes now carry per-change revisions; WebP/WebM bot
file identities cannot enter ordinary or rich photo inputs; legacy event and frozen callback reads
reject selected emoji content; and nested custom emoji checks every active ancestor. Complete literal
v4 incoming, changes, snapshot, document and frozen callback response oracles now cover these paths.
The focused follow-up gate passes 30 tests; its JUnit is retained at
`.scratch/custom-emoji-core-followup.xml` for coordinator collection. Scoped Ruff and strict mypy
remain green across the owned ten-file implementation/test selection. Checks use the
coordinator-owned untracked decoder from frozen dependency `4bcf4` and do not commit it.
