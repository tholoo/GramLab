# Carry ordinary documents through the public scenario runner

Type: task
Status: ready-for-agent
Work state: claimed
Owner: task/document-runner-v5-clean
Blocked by: implementation may proceed independently; integration requires verified native delivery104

The approved v5 document bridge exists in World and HTTP, but the public runner/CLI and Android
host accept only3/4. Simulation inline callbacks use4, and native rich-button observation and
verification use4 even when another message in the same persona's history contains a document.
A direct105 probe bypasses these public integration points. Complete this seam before claiming
that consumer scenarios can use documents through the library.

## Ownership and frozen behavior

Own this ticket, necessary version-selection changes in `src/gramlab/runner.py`,
`src/gramlab/__main__.py`, `src/gramlab/_android.py`, `src/gramlab/_android_rich_buttons.py`,
`src/gramlab/_interactions.py`, new `tests/test_document_runner_v5.py`, and the two stale v5
rejection expectations in `tests/test_emoji_runtime_selection.py`. No other existing test changes
are owned. Do not change World, Bot API, Android patches, shared docs, lockfiles, public defaults or
transport schemas. Coordinator owns integration and real Android execution.

Add explicit5 to runner, CLI and Android selection, retaining existing default3 and explicit3/4
behavior. Preserve strict rejection of booleans, nonintegers and unsupported versions. Never
silently upgrade/downgrade a requested Android version or omit unsupported content.

Simulation uses the latest supported World callback contract for ordinary inline callbacks so
it can carry a document message. This does not claim an Android protocol was selected or exercised.
Native rich-button snapshots, historical callback dependencies and pre/post-effect comparisons
must use the selected Android bridge version consistently. Rich-button observation supports4/5;
keep3 rejection and existing canonical targeting, journals, receipts and input safety unchanged.
The button protocol schema remains1, independent of the semantic bridge version.

A mixed persona history containing ordinary document, photo, custom emoji and rich-button messages
must retain all dependencies. Copy/disabled actions must compare complete unchanged World state;
callback actions preserve the exact original target revision/message and historical dependencies.
Audit fixed-v4 call sites for their actual role; do not mechanically replace unrelated legacy route
selection or storage schema constants. Report any additional necessary file ownership before editing.

## Acceptance and verification

Read TESTING.md and preserve an actual unsupported-version/ordinary-document-callback baseline red
before implementation. Exercise the public run/CLI boundary with a real contained scenario and
Bot API consumer, including forced-file send/reuse, original document inline callback delivery,
complete callback/update/history/event comparisons and simulation capture. Reuse original existing
fixtures; keep all private application data out of this repository.

For native-host orchestration, use established test boundaries to verify explicit v5 app
configuration and complete mixed-document snapshots during rich callback/copy/disabled verification,
with unchanged v4 controls and rejected v3 input. These host checks are not native-renderer proof.
Coordinator must then exercise the same public workflow on the reviewed v5 APK with actual input,
download/cache/restart, full semantic comparisons and original images. Integration is gated on104;
do not make the user-facing selector available before delivery is verified.

Run the focused new tests and affected existing runner/interaction/version-selection controls in
the offline namespace with fatal ResourceWarning, plus scoped strict typing and Ruff. No guest,
APK build, full suite, dependencies or upstream export. Freeze a clean task branch and report exact
red/green scope, source identities, terminal processes, required shared-doc updates and remaining
native acceptance. This task does not complete classification, albums, all button placements or
the operational milestone.

## Worker handoff

Implemented on `task/document-runner-v5` from
`5be733f1cab852869439dbdf2c43ce278dd9bcc4`. Explicit bridge v5 now reaches the runner, CLI and
Android host, while default3 and explicit3/4 remain unchanged. Simulation creates ordinary
document callbacks through World v5. Rich-button observation accepts selected v4/v5 and uses that
same version for its current snapshot, pre-effect snapshot, callback dependencies and post-effect
comparison; v3 rich input still rejects and the native button files remain schema1.

The retained pre-production run at `artifacts/document-runner-v5-red.xml` has two failures: the
runner rejects explicit5 before opening a missing manifest, and an ordinary-document simulated
callback reaches World as v4 and fails its v5 document requirement. After implementation,
`artifacts/document-runner-v5-green-02.xml` records 22 passes for the new acceptance, including the
contained public CLI/Bot API workflow. `artifacts/document-runner-v5-affected-01.xml` records 176
passes across the new test and affected runner, interaction, version-selection and rich-button host
controls under an isolated loopback namespace with fatal `ResourceWarning`. Scoped strict mypy and
Ruff check/format checks pass for every owned Python file.

No guest, APK build, full suite, dependency change or upstream export was run. The host rich-input
tests are boundary substitutes and make no native rendering or input claim. Coordinator acceptance
still requires the reviewed v5 delivery APK from task104 and the public native workflow named above.
Any public selector/compatibility documentation should be updated only after that native gate is
green. All worker commands completed without a retained terminal process.

## Document input identity correction

Independent review found that the first v5 document matcher accepted any nonempty accessibility
header above an exact caption. A wrong ZIP type or `999 GB` size with the same caption and keyboard
therefore reached the ADB tap boundary, while a correct PDF row became falsely ambiguous when a
different same-caption document existed. The retained pre-fix
`artifacts/document-runner-v5-descriptor-red.xml` records all three dispatch-boundary failures,
including both mismatched rows reaching the tap substitute.

The correction derives the stable English accessibility header from the target's immutable
persona grant and compares the original filename, extension/MIME fallback and formatted byte size
before admitting a cell. The history ambiguity guard resolves each document's own grant, so a ZIP
and PDF with the same caption remain distinguishable while two rows with identical observable
filename/type/size/caption still reject before input. Captionless documents remain untargetable.
This is an independent compatibility implementation based on pristine Android revision
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`: `ChatMessageCell.java:27105-27110` derives the
English document type from the attachment extension, `:27207-27215` appends the formatted size,
`MessageObject.java:6040-6059` supplies the original filename, and `FileLoader.java:1598-1609`,
`:1616-1631` and `:1644-1662` establish the filename-first MIME fallback. No Android/GPL source was
copied into the MIT module.

`artifacts/document-runner-v5-descriptor-green-02.xml` records 14 focused passes for exact
positive/negative dispatch and size/type boundaries. The affected host selection at
`artifacts/document-runner-v5-descriptor-affected-02.xml` records 42 passes across ticket107,
current-message interactions and rich button/list controls. This correction adds no bridge schema,
Android patch, guest or build claim; the native104 gate above remains unchanged.

## Clean-history migration verification

The reviewed worker tree was transplanted onto cleaned base
`545828bef33312043f3959a17e51715b10622761`. Legacy commits map to the clean commits as follows:

- `ae28870801ba318efd7b59dd0c7c36a3c5773e85` to
  `f9bd4d332ff1af566ba0dcaadc38959b472cf6f9`;
- `f78769264b6041f9db1a8a216e9094fea31b452e` to
  `f662f8f8f05754cc20bd11be51214b56e9624f3c`;
- `27b7bd85556415f853a180ceb690c7751d9d0475` to
  `f1d82cc9d1058b0fc50ddbf879e227d0f82870ee`; and
- `80934bc056786fdd548727f01b9678f29f2edf1c` to
  `e80aa6ce6d433e75cd81008637902bd6fda8ab23`.

The clean tip's eight owned files match the frozen legacy tip exactly, its base is an ancestor,
and `git diff --check` passes. The first clean full-file attempt at
`artifacts/document-runner-v5-clean-01.xml` was invalid because its missing artifact parent caused
24 setup errors after11 passes; it is retained only as harness evidence. The corrected pinned-shell
run at `artifacts/document-runner-v5-clean-02.xml` records all35 cases passing in6.07s.

The first affected rerun at `artifacts/document-runner-v5-clean-affected-01.xml` was also an invalid
harness invocation: running the virtual environment directly omitted the provisioned Nix runtime,
so39 cases passed and the three contained public runner cases reported `supervisor_failed`. The
same exact42-case selection then passed in7.10s under the pinned shell and loopback-only namespace:

```sh
tools/dev default --offline --command unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; PYTHONWARNINGS=error::ResourceWarning .venv/bin/pytest \
  tests/test_document_runner_v5.py \
  tests/test_android_current_message_interactions.py::test_composer_uses_configured_snapshot_for_current_visible_messages \
  tests/test_android_current_message_interactions.py::test_rich_photo_caption_identity_matches_text_and_credit_and_rejects_ambiguity \
  tests/test_android_current_message_interactions.py::test_ordinary_photo_keyboard_requires_exact_authored_caption_and_rejects_ambiguity \
  tests/test_runner_rich_buttons.py::test_rich_inline_real_bot_callback_and_edit \
  tests/test_runner_rich_lists.py::test_rich_lists_real_bot_callback_edit_and_cold_reopen \
  --junitxml=artifacts/document-runner-v5-clean-affected-02.xml'
```

Scoped strict mypy with `MYPYPATH=tests`, Ruff check and Ruff format check all pass over the five
owned production modules and two owned test files. The editable import resolves to this clean
worktree. The coordinator explicitly approved the two updated v5 rejection expectations in the
existing emoji runtime selection test. No Android guest or build was run, so integration and public
native acceptance remain gated on verified native delivery104.
