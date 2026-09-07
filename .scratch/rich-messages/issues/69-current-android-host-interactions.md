# Honor current message shapes in Android host interactions

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: native execution requires coordinator disk-space cleanup approval

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

Read AGENTS, handoff, TESTING, offline safety and parallel workflow. Provision and execute checks
through this checkout's `tools/dev default --offline --command ...`; never use an inherited runtime
profile with a bare command. Run focused host regressions, native collection and scoped
Ruff/format/strict typing only. No guest/build/full gate. Retain red/green evidence and return a
frozen clean commit with all processes terminal; coordinator owns integration and native acceptance.
