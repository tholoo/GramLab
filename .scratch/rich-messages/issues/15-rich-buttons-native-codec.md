# Project rich buttons through the original native codec

Type: task
Status: claimed
Work state: resolved
Assigned branch: task/rich-buttons-codec
Assigned worker: rich_button_seam
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

## Worker handoff

The canonical codec fixture/probe/test checkpoint is `d166ae84bf0e8d8c571062a821314a5f13f94d1d`.
Those four files remain frozen for coordinator-owned existing-APK red. The fixture server is
loopback-only and capability-authenticated, using a real baseline World snapshot with separately
authored canonical rich content. It deliberately proves native codec behavior only.

Patch 0013 modifies only the two assigned GPL adapter/probe classes. It projects original row,
page-button, inline-text-button, style and callback/copy/disabled constructors; rejects malformed
or noncanonical records; preserves UTF-8 callback bytes; validates copied-text code points and
canonical plain-label leaves. BridgeProbe observes the complete serialized content and checks
native style/alignment/optional-style/password flags. No upstream renderer, UI, input or assets
changed; no client-derived code entered the MIT core. Fixture JSON and Python are independently
authored contract examples and reuse the repository's existing authenticated codec transport.

The complete catalog covers eight-button fill rows, all explicit alignments, absent/all styles,
all actions in row and inline positions, nested plain arrays and currently admitted RichText roles.
Four independent positives distinguish 256 Unicode code points from Java UTF-16 units, 64 UTF-8
callback bytes, the last allowed multibyte label character, and per-leaf direction normalization.
There are 51 static malformed records and six generated length/depth/node/aggregate-byte cases.
Full observed message metadata and complete rich content are compared, with exact rejection errors.

Verified in the worker's independent offline tool profiles and editable environment:

- Scoped Ruff lint, formatting and strict mypy for both new Python files passed.
- Scoped JDK 17 compilation of the two changed GPL classes against the approved immutable main
  compiled classes and Android 36 SDK passed. This is not an APK or native behavioral check.
- A fresh private export of pinned Android revision `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`
  accepted the complete 13-patch queue and reproduced both authored GPL files exactly.
- 10,759 original UI/resource/asset files compared directly against pinned Git blob identifiers;
  zero differences. The source and prepared exports remain in this worker's ignored cache.

Retained worker evidence: `artifacts/rich-buttons-codec-static/` contains scoped check logs,
`source-integrity.json` and `verification.json` with exact local provenance/tool paths. Reproduce
Python checks with `tools/dev default --offline --command uv run --offline` followed by
`ruff check`, `ruff format --check`, or `mypy` and the two owned Python paths. Reproduce preparation
with that shell's Python, `clients/android/prepare.py`, the approved pinned `--upstream` and a
new private `--destination`. Source acquisition was unnecessary.

Deferred to coordinator: run
`tests/test_android_rich_button_codec.py::test_canonical_buttons_survive_native_serialization_and_reject_malformed_snapshots`
under the Android profile, shared serial lock and documented outer network guard, first against
the existing APK for red and then rebuilt APK for green. Native red/green, full/static integration
lists, real-bot/button-input acceptance and shared compatibility/handoff docs remain coordinator
work. No native acceptance is claimed here. No guest, APK build or worker background process was
started or remains running. Ticket remains claimed until coordinator acceptance.


## Coordinator regression checkpoint

The frozen codec fixture checkpoint was executed against the preceding list-capable APK before
native source changes. The plain codec baseline, zero accounts and guest network/filesystem
isolation pass. The valid rich-button catalog fails with `GRAMLAB_BRIDGE_UNSUPPORTED_RICH_BLOCK`;
one failed test in 79.67 seconds. This is the expected native red, not a startup failure. Its
terminal run retains complete codec observations and JUnit in ignored coordinator artifacts.
Integrated positive execution and APK build remain pending.


## Integrated native checkpoint

The normal 13-patch APK builds offline in 2 minutes 50 seconds. The codec case passes in
104.79 seconds with complete catalog/metadata, four valid boundaries, 57 exact rejections and
baseline/isolation checks. The independent real-bot simulation passes in 1.23 seconds after
integration. Original native rendering/live RTL edit/cold restart passes in 67.08 seconds with
complete canonical serialization, zero accounts and guest isolation. All three original PNGs were
visually inspected. The serial Android gate stopped after 19 passes on an older catalog expectation, now tracked
in [ticket 20](20-canonical-catalog-regression.md); this ticket remains claimed pending the
failed and unexecuted cases on the same immutable normal APK. No geometry instrumentation
or button input is part of the normal APK/rendering check.

## Combined normal Android acceptance

All 22 failed-or-unexecuted cases pass on continuation in 1,143.57 seconds. Together with the
19 unaffected retained passes, the exact 41-case collected inventory is covered without skips on
the same immutable normal APK. The stopped 19-pass/one-failure run remains retained; this is
resumed gate coverage, not one uninterrupted green run. The comprehensive catalog's correction
is fixture-only, with complete World/native equality and a fast regression. The full core gate
now passes 370 cases in 58.87 seconds at 81.03% coverage. Experimental geometry/input remains a
separate acceptance boundary.
