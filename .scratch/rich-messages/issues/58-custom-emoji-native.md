# Resolve custom-emoji documents through original Android loaders

Type: feature
Status: ready-for-agent
Work state: claimed by custom-emoji-native worker
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

## Worker handoff

Task `custom-emoji-native`, branch `task/custom-emoji-native`, assigned base
`feef4b848206f6c49a49518caffecd7f85c44d48`. Owned changes are this ticket, new patch 0024,
its series/README entries, and the two new custom emoji codec files. No earlier patch, shared
source, core module, renderer, input handler, fixture media, build manifest or lockfile changed.

The patch changes eight GPL sources: Bridge, new GramLabCustomEmoji, Media, RichMessage,
Runtime, FileLoader, AnimatedEmojiDrawable and BridgeProbe. V4 dependencies are response-local
until complete validation; exact change/callback dependency sets are checked before publication.
Snapshot identity locking covers revalidation, metadata commit and remembered profiles together.
Canonical original Documents retain full signed-64 logical IDs, DC -1, ordinary document
attributes and explicit layer127 thumbnail asset locations with local ID 2. Snapshot metadata
never inserts original Documents in their memory/SQLite caches. The original request dispatch
performs bounded authenticated lookup, exact set validation and Vector projection. Original
non-Vector local failure removes and clears only the captured pending callback owner; it does
not invoke null, cache a sentinel, or retry automatically.

Document and ImageLocation calls share the existing verified complete-file lifecycle with
original media types, destinations, filename cancellation, progress and terminal delegates.
Reserved streaming rejects before queue/DC entry. Cancel-all now also cancels registered local
transfers under the same lifecycle lock, disconnecting outside it. The existing reserved-zero
ImageLoader registration guard automatically covers the extended reserved Document predicate;
no additional ImageLoader or rendering change is required.

Verification completed without APK compilation or a guest:

- Eight normal23 preimage SHA-256 fingerprints still match the read-only coordinator source.
- `patch --batch --fuzz=0 -p1` in a fresh private preimage copy: all eight changed sources apply
  with zero offsets; every result matches the private authored after-image byte-for-byte.
- `tools/dev default --command uv run ruff check` on the two owned Python files: pass.
- `tools/dev default --command uv run mypy` on the same files: pass, two files checked.
- Focused `pytest --collect-only`: one batched native codec test collected; no guest executed.
- Offline-guarded fixture construction/JSON round trip: 99 uniquely named independent cases,
  13 positive and 86 rejected cases, with full native-result literals.
- `git diff --check`: pass. Private source fingerprints, applicability and fixture counts are
  retained in ignored task storage; no acquired source or host configuration is committed.

The codec matrix covers original Document attributes, static/animated duration, maximum IDs,
legacy thumbnail serialization and key collisions; ordinary UTF-16/order/caption/incoming
entities; recursive/empty-alternative/button rich nodes; live/frozen dependencies; immutable
reconnect conflicts; malformed metadata, invalid IDs, exact document lookup sets and unknown/mixed
lookup errors. Metadata fixture bytes are intentionally not decoded or downloaded by this codec
suite. Each case uses a fresh app_process within one guest startup; no World/cache lifetime is
shared between vectors.

Native red/green remains unavailable to this worker by assignment. Coordinator must compile,
run the batched codec matrix, and prove original static rendering, transparent VP9 animation,
empty-cache document lookup, transfer cancellation/coalescing/failure, unchanged cold-cache reuse,
unknown/mixed callback cleanup and explicit cold-restart recovery. More than 200 IDs in one
original resolver request rejects at the frozen request bound; no batching/automatic retry policy
is invented. Runtime streaming is explicitly unsupported for reserved local files. Source checks
do not establish decoder behavior, absence of a native cache write, or UI recovery.
