# Honor current message shapes in Android host interactions

Type: bug
Status: ready-for-agent
Work state: frozen for coordinator review on `task/current-android-host-interactions`
Blocked by: coordinator native execution result

Own this ticket, `src/gramlab/_android.py`, new `tests/test_android_current_message_interactions.py`
and, if needed, one new self-contained `tests/fixtures/current_message_interactions_bot.py`.
Do not edit other core files, native patches, existing tests, shared docs or runtime profiles.

The public-path audit identified two concrete host defects. `_send_composer_action` and
`_accepted_composer_send` hard-code World snapshot version2 even when this Android instance uses
bridge3/4. A visible photo or explicit mention then rejects a v3 composer operation; visible
custom emoji rejects v4. Snapshot scope is persona-wide, so an unrelated chat may trigger it.
Both call sites must honor the instance's configured bridge version without weakening World
legacy guards or changing native defaults. Second, `_inline_fragments` passes rich photo caption
objects directly to `_rich_text`; canonical captions are `{text, credit}` wrappers, including
credit-only captions, and need their own traversal. Keep canonical text order, hidden-details
exclusion, ambiguity rejection and the original hit-testing rules unchanged.

Establish meaningful reds at the relevant host/World boundary before narrow fixes. Use real World
messages and snapshot/send journals; avoid stubbing production validation or merely asserting a
version keyword. For the caption matcher use independently authored native-style label text and
real canonical caption shapes to show valid matching and absent/ambiguous rejection. Where a
host preflight needs an external Android peer, explicitly distinguish a bounded external-input
substitute from actual native evidence. Do not claim pixels/input from host tests.

Prepare one compact actual public runner/Scenario native regression covering a rich photo caption
with ordinary inline keyboard, real callback, and a composer send when photo/mention/custom-emoji
content is visible. Keep complete expected histories, callback snapshots and sends. Reuse original
fixtures and the current reviewed APK; no renderer, profile or bridge-schema changes. Native case
must be marked Android and will remain unexecuted until the coordinator runs it with disk space.
If one combined scene cannot prove a boundary, state the gap rather than inventing success.

The coordinator added one same-file observation during implementation: original Android exposes a
captioned ordinary photo as `Photo\n<caption>\nReceived at ...`. Ordinary photo keyboards therefore
also use the exact authored caption as their identity. Generic `Photo` and receipt metadata cannot
identify a message; captionless photo-keyboard input remains unavailable without another sound seam.

Read AGENTS, handoff, TESTING, offline safety and parallel workflow. Provision and execute checks
through this checkout's `tools/dev default --offline --command ...`; never use an inherited runtime
profile with a bare command. Run focused host regressions, native collection and scoped
Ruff/format/strict typing only. No guest/build/full gate. Retain red/green evidence and return a
frozen clean commit with all processes terminal; coordinator owns integration and native acceptance.

## Worker acceptance

- The retained focused red has four failures: photo and mention v3 plus custom-emoji v4 composer
  preflight all hit the legacy v2 guard, and a World-canonical rich photo caption raises
  `KeyError("type")` during identity extraction.
- Both composer snapshots now use the configured Android bridge version. Focused tests retain the
  real World message, version guard, client-send journal, position and final history while clearly
  labeling the substituted native input boundary.
- Rich photo captions traverse canonical `text` then `credit`. Captioned ordinary photos match only
  the observed native wrapper containing their exact authored caption. Missing fragments, changed
  captions, duplicate native cells and captionless photos reject conservatively. The final
  history-wide ambiguity guard uses the same authored identity: distinct ordinary photo captions
  reach the native input boundary, while a repeated exact caption remains ambiguous.
- One collected Android test stages a public bridge-v4 runner with a contained multipart bot, rich
  photo caption and keyboard, mention, custom emoji, native callback and native composer send. It
  independently specifies all fields of the six-message canonical history, including the photo
  descriptor and complete mention/custom-emoji messages, then asserts callback records/events and
  the send journal. Publication and post-interaction polling have separate deadlines, and the bot's
  fixture-only wait remains bounded by the existing 300-second run budget. The Android case was not
  executed because native disk approval remains pending.

Evidence is retained under `artifacts/ticket69-red.xml` and
`artifacts/ticket69-host-green-final.xml`; the intermediate malformed-test failure remains in
`artifacts/ticket69-host-green.xml`. Final host result: 5 passed, 1 Android deselected. Collection:
6 tests. The follow-up result is retained at `artifacts/ticket69-followup-host-green.xml` with the
same 5 passed and 1 Android deselected. `artifacts/ticket69-followup-ambiguity-red.xml` retains the
old final guard rejecting two distinct captioned photos solely because both have empty `text`.
Scoped strict mypy reports 3 source files clean; scoped Ruff lint and format pass.

## Coordinator integration

Frozen worker tip `4659dc288a255398c53abfeb4c3cd096ce9b650b` is integrated. The five
host regressions and public capture/callback controls pass seven tests in 4.01 seconds, with
one Android case explicitly deselected. Scoped Ruff/format and strict typing pass all three
Python files. The combined core gate passes 652 tests at 85.44% coverage in 87.04 seconds; the required original native case remains
unexecuted, so this ticket stays claimed. The independent review caught the empty-text history
ambiguity guard and fixture deadline/oracle defects before integration; their corrected worker
evidence is retained.

## Current execution

Disk cleanup is complete. The coordinator has started the original public native regression
with immutable normal27, which includes the reviewed bridge-v4 support. Native acceptance is
not claimed before that run terminates and its complete assertions pass.

The first native run completes the actual callback/composer flow and exact six-message history,
then fails in 83.41 seconds because the test compares a creation event to a receipt that includes
`answer: null`. The independent expected callback now explicitly separates the six creation
fields from the receipt answer field. Scoped lint/format/strict typing pass; the fresh corrected
native run remains the acceptance boundary. The original failed JUnit is retained.
