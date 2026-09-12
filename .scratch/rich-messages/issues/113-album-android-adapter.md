# Carry complete albums through the original Android adapter

Type: task
Status: ready-for-agent
Work state: open
Owner: unassigned
Blocked by: 112

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
