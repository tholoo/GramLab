# Inline callbacks on rich bot messages

Type: task
Status: claimed
Work state: ready for coordinator integration — rich_inline, task/rich-inline
Blocked by: none

## Ownership

Worker owns src/gramlab/_android.py, tests/test_runner_rich_buttons.py (new), examples/rich_inline/
(new), and this ticket. Coordinator owns shared docs, integration, full gates and effects probes.
No world/API changes or renderer changes are assigned. Request ownership changes first.

## Contract and acceptance

The existing public tap_inline_button(chat_id, message_id, row, column) must handle the supported
rich-message subset through an actual accessible native button. Preserve ordinary text targeting,
full-keyboard matching, ambiguity/stale/viewport rejection, one actual tap, no automatic retry,
full callback verification and failure evidence. Do not synthesize an Android callback.

Inspect pinned native accessibility construction before choosing a rich target identity. Match
observable text and keyboard to the requested authoritative message conservatively. Different
world messages with indistinguishable accessible content must fail before a tap, including an
off-screen duplicate. Metadata/formatting differences alone do not establish native identity.
Never silently use only a repeated button label, arbitrary coordinates or the rich message's
empty ordinary text. If current accessibility cannot identify a supported target, report the
specific gap and consult the coordinator before adding a native observation seam.

Provide a real-bot example in simulation and Android modes: rich bilingual content plus a
repeated-label callback keyboard, select the intended row/cell once, answer the callback and edit
the rich message. Assert complete initial/callback/final content and equivalent semantic outcomes;
retain original captures and report. Add an ambiguous-rich negative case that preserves earlier
evidence and creates no callback. Keep existing plain inline negative cases passing.

Establish the native red at the current target boundary before the fix. Use the already verified
read-only APK and one focused guest case at a time under android-gate. Do not rebuild the APK or
run a full gate. Coordinate lock availability with root; focused core checks use the outer network
guard. Commit only owned files and leave this ticket claimed for root's integrated acceptance.

## Worker observations

The independently authored example uses a real standard-library HTTP bot, a heading, bilingual
row-major table cells, styled Persian/English paragraph and repeated Confirm labels. It selects
row 1/column 0, compares the complete Bot API callback message to the sent reply, edits to an RTL
rich paragraph and answers once. The host checks complete history, callbacks and captures.
Run-scoped callback UUID/chat-instance values are checked separately when comparing event streams.

At the pinned Android revision, `ChatMessageCell` accessibility emits visible rich block text
with localized block labels, then a separate received-date paragraph; keyboard buttons remain
children of that same host node. `RichMessageLayout` table text follows caption and row-major
cells. Closed details hide their descendants, and formatting/RTL is not an identity channel.
Source observations guide an independent observation matcher, not a copied renderer or label model.

The first native attempt failed during initial activity launch, before any rich input. It remains
separate startup-failure evidence. One fresh unchanged trial then established the real red:
heading, table, paragraph and full keyboard rendered, but the text-only target lookup failed with
“Inline message and complete keyboard must have one accessible match”; no callback was created.

The rich matcher now passes both focused native cases: 81 seconds for real callback/edit parity,
and 103 seconds for the off-screen duplicate rejection. The negative retains three original
captures, shows one matching native host in the viewport and rejects the second rich message
because an earlier bold-styled equivalent remains in history. Its first callback is preserved;
there is no additional callback or world mutation. Original positive and ambiguity PNGs were
inspected. Seven focused public core callback/capture tests pass in eight seconds. Focused Ruff,
format and strict mypy checks pass. Both existing plain-native regressions also pass: ordinary callback/edit parity in 95 seconds and
ordinary ambiguity rejection in 78 seconds. No test was skipped. All worker-owned process handles
are terminal and guest locks are released.

The pinned English host's receipt paragraph is excluded from identity. Plain messages retain a
complete text-prefix boundary; rich text wrappers concatenate within fields while ordered fields
remain observable separately. Whole-history ambiguity checks exclude styling and closed-details
contents as distinguishing evidence. The full keyboard, enabled state, viewport, stale-message
check and single native tap remain required. Missing/empty observable content or unknown host
metadata fails explicitly. Conservative rich fragment containment can reject otherwise distinct
messages; this limitation is recorded in the example README.

The existing APK remains read-only; no native patch, renderer/resource modification or runtime
graphics change belongs to this task. The full product and broader rich input inventory remain
open. Keep this ticket claimed until the coordinator verifies and integrates the branch.


## Focused reproduction

Provision the existing approved APK and use `tools/dev android --offline` with the documented
outer network guard. Select these scopes rather than a worker-owned full gate:

- Core: `tests/test_runner_rich_buttons.py tests/test_runner_interactions.py
  tests/test_runner_rich_capture.py -m "not android"`.
- Native under `android-gate`: `tests/test_runner_rich_buttons.py -m android`.
- Existing native regressions: the ordinary inline positive and ambiguous-target tests in
  `tests/test_runner_android.py`.
- Static: Ruff check/format and strict mypy on `_android.py`, the new host test and
  `examples/rich_inline`.

The coordinator owns shared documentation/matrix and CI/contributor typing-list updates. The new
example README records usage and native identity limits. The full integrated gate remains the
coordinator's responsibility. The initial unrelated startup failure remains unresolved; later
passes do not establish its cause or claim a startup fix.


## Coordinator review follow-up

The native tests now use the existing infrastructure guard: unavailable Android profile, approved
APK or KVM yields an explicit skip before starting a run. A missing-APK check confirms all three
marked tests skip.

Review identified an ordinary-message regression in whole-history ambiguity scanning: another
plain message equal to the first line of a multiline target was treated as a duplicate. The new
real-bot native regression retains that separate first-line message without a keyboard and must
still select the complete multiline target once. The native red first rendered both messages, then falsely rejected the requested multiline
target as ambiguous without creating a callback. After restoring exact full-text equality for
ordinary/ordinary comparisons, the same native test passes in 71 seconds with one actual tap,
complete original callback content, bot edit, identical simulation/Android world and history,
and two original captures. Both green captures were inspected. Comparisons involving rich
messages retain conservative observed-content checks. Focused Ruff/format/mypy checks pass;
no APK, renderer, timeout or input-retry behavior changed. The two review-run handles are terminal
and the shared guest lock is released. Earlier feature evidence remains recorded separately;
this follow-up ran only the requested native red/green pair, not a repeated full gate.
