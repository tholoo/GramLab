# Inline callbacks on rich bot messages

Type: task
Status: ready-for-agent
Work state: unclaimed
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
