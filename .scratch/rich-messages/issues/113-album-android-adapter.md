# Carry complete albums through the original Android adapter

Type: task
Status: ready-for-agent
Work state: claimed
Owner: album-android-adapter
Blocked by: none

Worker dependency handoff: the coordinator authorized read-only use of the pinned primary-checkout
Android upstream tree and the retained normal30 APK. The worker verified upstream
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c` and APK SHA-256
`a964bbaccaaf59719d966a72ecd85de4288d146887e3f7ff7d50be7281df726b`; all generated source and
evidence remain isolated in this worktree.

After bridge v6 is accepted at the host boundary, add patch
`clients/android/patches/0032-atomic-media-groups.patch` after the approved rich-detection patch. It
maps canonical group IDs to `TL_message.grouped_id`, validates complete group topology, recovers
split cursors through a v6 resnapshot and applies each live creation group through one stock
`TL_updates` batch before advancing the cursor. Own only
`clients/android/patches/0032-atomic-media-groups.patch`, the patch series/readme,
`tests/fixtures/android_media_groups/**`,
`tests/probes/android_media_groups_codec.py` and `tests/test_android_media_groups_codec.py`.
Do not modify original renderer/layout classes or recreate album presentation.

The patch and every Java probe/fixture that imports, reflects over or serializes Telegram Android
classes are GPL-2.0-or-later with an SPDX header and existing COPYING/notices. Independently authored
Python orchestration/oracles remain MIT. Copy no Android source or schema into MIT core and acquire
no new upstream asset.

Audit every v5→v6 seam: exchange/schema detection, configuration allowlists, `GramLabMedia.Scope`,
document requirements/transfers, all media/custom-emoji/callback/message route builders and
allowlists, exact-field sets and authority equality. Prove malformed/noncanonical/zero/overflow IDs,
cardinality, contiguous-run/message/position ordering, duplicate/disjoint/interleaved groups,
complete snapshot/change/difference behavior, split-cursor recovery and retained-superset snapshot
versus exact response-local dependencies. Carry the grouped-edit branch selected in ticket111.

Freeze independently authored fixtures and obtain normal30's unsupported-v6 red first; then pass
static patch/application checks. The worker hands off a committed patch and tests. The coordinator
builds/provenances normal31 once and completes the focused app-process codec gate on that APK before
integration, retaining ownership of the APK and shared docs.

## Worker implementation evidence

- Patch 0032 changes exactly five GPL client files: `GramLabBridge`, `GramLabMedia`,
  `GramLabRuntime`, `FileLoader` and `BridgeProbe`. It does not touch the renderer, grouped layout,
  resources or input handlers. Its SHA-256 is
  `442dcc4d5e9f6fbb8a75bfe6db4e23a69f157e3c03a20ee111653c5b185e6f9a`.
- `.cache/album-adapter-stage02/stage.json` is `ready`: all five preimages and postimages matched,
  no files were added, and system `patch --batch --fuzz=0 -p1` reported no fuzz or offset. A fresh
  complete export at `.cache/album-adapter-source32-green-02` applied all 32 patches and matched the
  five independently recorded postimage hashes byte-for-byte. The authorized upstream remained
  clean at `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`.
- The independently authored oracle freezes 35 cases across all ticket boundaries. The test module
  collects five tests: three host/static tests plus the normal30 red and album-era green native
  selectors. Focused host/static tests plus the complete patch-staging suite passed 18/18. Ruff
  check/format and strict mypy passed for both Python files. The adjacent button-disarm, document
  codec/UI and rich-auto-detection host suites passed 13 tests with their four native-only cases
  skipped as expected.
- The GPL launcher compiled from a clean output directory with javac 17/API 36/D8 36.0.0. Source
  SHA-256 is `9c4f214e9411008395ef2b1fb14675e1baadb761c82206079764fecb4ff874c8`;
  the reproducible probe APK SHA-256 is
  `9e3138154e0a89a3321bbeac0c59a8365c5b142258c0232e40eb7d8a14c64021`.
- The only worker Android run was
  `test_actual_pre_album_apk_rejects_bridge_v6` against the verified immutable normal30 APK. It
  passed 1/1 with app-process exit 2 and `GRAMLAB_BRIDGE_INVALID_DATA`, zero HTTP requests and one
  unconsumed snapshot, proving that pre-album Android rejects v6 before transport. The API 36 x86_64
  guest ran under the shared `android-gate`, user/network namespace containment and loopback-only
  fixture with zero accounts and no build/download. Evidence is retained in
  `artifacts/album-adapter-normal30-red-01.xml` and
  `artifacts/album-adapter-normal30-red-01/test_actual_pre_album_apk_reje0/`. The emulator stopped,
  its dedicated AVD and duplicate APKs were removed, and the lock was released.

## Deliberate boundary

Public tracked-host selection of bridge v6 is intentionally deferred to ticket114. In particular,
ticket113 does not alter `src/gramlab/_android.py`, `runner.py`, `__main__.py`,
`_android_rich_buttons.py` or `_interactions.py`. The coordinator may exercise the ticket113 green
through its direct contained app-process selector on the fresh album-era APK; this worker does not
claim that the public runner selects integer 6 yet. The album-era build, provenance and green native
codec remain coordinator-owned.
