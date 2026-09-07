# Resolve custom-emoji documents through original Android loaders

Type: feature
Status: ready-for-agent
Work state: open
Blocked by: none for adapter implementation; core v4 required for integrated acceptance

Own this ticket and new `clients/android/patches/0024-local-custom-emoji.patch`, plus its series
entry and task-specific explanation in `clients/android/patches/README.md`. Own new
`tests/probes/android_custom_emoji_codec.py` and `tests/test_android_custom_emoji_codec.py` for
independent literal valid/rejected codec cases. Do not edit earlier patches, shared docs, Python
production, media fixtures, lockfiles or the coordinator's prepared source/APK.

Implement the frozen neutral v4/documents and GPL projection/resolver/loader contract in
[the implementation contract](../../../docs/development/custom-emoji-implementation-contract.md).
Preserve all v1–v3 behavior and normal original rendering. Keep logical IDs separate from assets;
verify layer127 thumbnail round trips and key collisions. Snapshot metadata may populate only the
authorized transfer registry, not the original Document memory/SQLite cache. Preserve original
requests/caches/delegates; route Document and ImageLocation through shared authenticated transfer.
Unknown/mixed failures release only failed pending callbacks without null invocation or automatic
retry. Cover reserved streaming entry points, stale lookup ownership and explicit cold recovery.

Prepare patched source in a private ignored directory derived from the verified normal23 baseline,
preserving pristine upstream/earlier patch inputs. Do not run a build or guest without coordinator
assignment; coordinator owns serial builds and native acceptance. Check patch applicability and
independent codec fixture shape/static checks first. A Python-only result is not native proof.
Do not create a mock renderer or weaken required fields to get a fixture accepted.

Read AGENTS.md, licensing/upstream, TESTING.md and parallel-work.md. Claim/check the assigned
worktree, use its tools/dev and verify imports, commit only owned files, and send a frozen clean
tip with source/patch checks, remaining native checks and all owned process handles terminal.
