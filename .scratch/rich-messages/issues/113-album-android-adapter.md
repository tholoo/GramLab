# Carry complete albums through the original Android adapter

Type: task
Status: ready-for-agent
Work state: resolved
Owner: coordinator
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
  `1ccd93f32530b6bd313652607889187d97c0df007ef11a0c69561a2a87507135`.
- `.cache/album-adapter-stage03/stage.json` is `ready`: all five preimages and postimages matched,
  no files were added, and system `patch --batch --fuzz=0 -p1` reported no fuzz or offset. A fresh
  complete export at `.cache/album-adapter-source32-green-03` applied all 32 patches and matched the
  five independently recorded postimage hashes byte-for-byte. The authorized upstream remained
  clean at `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`.
- The independently authored oracle freezes 48 cases across all ticket boundaries. The follow-up
  cases prove response-wide chat/message uniqueness in both changes and difference, contiguous
  snapshot group revisions, reordered rejection, complete ten-member and consecutive groups,
  exact limit-one and limit-1,000 expansion, and valid v5 snapshot/changes/messages behavior. The
  test module
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
  its dedicated AVD and duplicate APKs were removed, and the lock was released. The review
  follow-up did not change the launcher, Python guest protocol or explicit normal30 input, so this
  retained red remains valid and was not rerun.

## Deliberate boundary

Public tracked-host selection of bridge v6 is intentionally deferred to ticket114. In particular,
ticket113 does not alter `src/gramlab/_android.py`, `runner.py`, `__main__.py`,
`_android_rich_buttons.py` or `_interactions.py`. The coordinator may exercise the ticket113 green
through its direct contained app-process selector on the fresh album-era APK; this worker does not
claim that the public runner selects integer 6 yet. The album-era build, provenance and green native
codec remain coordinator-owned. Native execution proof for runtime `processUpdates` batching, UI
resnapshot reconciliation and cursor advancement is likewise deferred to ticket114; ticket113 owns
their reviewed/static adapter sequencing and the direct bridge codec contract only.

## Coordinator build and gate sequencing

The reviewed adapter was integrated at `d840f2f` and one fresh contained normal31 build completed
from the pinned upstream plus all 32 patches. Its immutable APK has SHA-256
`e60a873fc0283b270a35538c63a5f6e701e74cfecb8f10cfce35af670c57be7a`; ignored source provenance is
retained at `.cache/local-notes/normal31-build-provenance.json`. To preserve the approved limit of
exactly three normal31 guests, the app-process green is combined with ticket114's first focused
album guest rather than booting a fourth codec-only guest. This ticket remains claimed by the
coordinator until that combined gate passes.

The combined focused gate passed on unchanged normal31 in
`artifacts/album-normal31-focused-04.xml`. All48 independently authored app-process cases passed,
including exact v5 compatibility, literal-null rejection, grouped topology, complete paging,
atomic applications and split-cursor recovery. The same guest then passed the original stock album
UI/transfer/restart acceptance described in ticket114. The retained client copy SHA-256 is the
immutable normal31 value above, the report embeds five manually inspected original screenshots,
and IPv4/IPv6 denial, loopback-only local transport and zero Android accounts passed. This closes
the adapter's pending native green without another codec-only guest or any APK rebuild.
