# Project rich buttons through the original native codec

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none for independent canonical codec; ticket 14 for real-bot execution

Implement the GPL side of the frozen [button contract](../../../docs/development/rich-buttons-contract.md).
Own new clients/android/patches/0013-rich-button-projection.patch, clients/android/patches/series,
new clients/android/fixtures/rich-message-buttons.json and rich-message-invalid-buttons.json,
new tests/probes/android_rich_button_codec.py, new tests/test_android_rich_button_codec.py and
this ticket. Existing patch files, shared guest/probe helpers, global docs, core and renderer
remain coordinator-owned. Use a separate task branch/worktree.

The additive patch extends GramLabRichMessage and BridgeProbe only. Cover canonical callback,
copy and disabled row/inline constructors, styles, alignment and recursive plain label arrays.
Keep original RichMessageLayout, UI, assets and native input unchanged. Independent fixture
expectations must retain the complete rich message after native TL serialization. Reject malformed
and noncanonical styles/alignment/actions, wrong types, bounds and unsupported label entities.
Preserve inherited aggregate budgets and account for code points versus Java UTF-16 units.

Use the existing list codec fixture-server pattern for a separate authenticated loopback-only
codec probe. It supplies independent canonical snapshots, not invented real-bot acceptance. First
record red against the old prepared code or hand coordinator the exact native red check before
its APK changes. Worker may prepare private source and run scoped Java/static checks with the
already provisioned immutable tools, but must not build an APK or start a guest. Read licensing
and upstream guidance before adapting any source. No network acquisition is needed.

Run scoped Python lint/format/mypy and validate patch application against a private pinned export;
verify all original UI/resources remain unchanged. Report checks that require coordinator execution
explicitly. Commit owned files and hand back a frozen clean branch, retained evidence and exact
reproduction. Coordinator owns shared static lists, APK build, native red/green, real-bot/input
acceptance, shared docs and combined gates. No public targeting/geometry API is assigned.
