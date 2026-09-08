# Carry ordinary documents through the public scenario runner

Type: task
Status: ready-for-agent
Work state: open
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
