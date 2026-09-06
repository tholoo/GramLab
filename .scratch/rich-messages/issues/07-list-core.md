# Model complete structured rich-list input and output

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

## Ownership and interface

Python worker owns src/gramlab/rich_messages.py, tests/test_rich_messages.py,
tests/test_rich_bot_api.py and this ticket. No Android, capture/inline walker, example, shared-doc
or dependency changes are assigned. The coordinator owns integration and combined checks.

Follow [the pinned contract](../../../docs/development/rich-list-references.md). Add the single
`list` block with nonempty `items`. Each input item requires `blocks` (including an empty array),
and permits only has_checkbox, is_checked, value and type. Preserve all currently supported nested
blocks recursively, including nested lists. Validate booleans and signed 32-bit integers strictly;
type is empty/absent or a, A, i, I, 1. Every item must agree on ordered versus unordered status,
but ordered items may mix valid label types and arbitrary values. Missing value defaults to zero.

Canonical output items always have label and blocks. Unordered label is the bullet and omits
type/value; ordered labels follow the pinned alphabetic/Roman/decimal rules and retain type/value.
False flags omit; checked without an enabled checkbox normalizes away. Value without nonempty
type normalizes away after validation. Output-only label is rejected in public input under the
existing unknown-field policy. Empty item blocks are preserved, not filled or rejected; other
existing nonempty-block limits remain unchanged. Existing tree/UTF-8/node budgets cover input and
expanded canonical output. No new local restriction is authorized merely to simplify rendering.

The coordinator-authored clients/android/fixtures/rich-message-lists.json is a canonical native
catalog, not public input. Treat it as a shared interface example; use independent input and
expected fixtures in public-boundary tests. Do not import client implementation into the MIT core.

## Acceptance and verification

Establish a missing-list red before implementation through World or real HTTP. Verify complete
JSON and form sendRichMessage and rich edit responses; canonical storage, snapshots/differences,
event ordering, reopen and callbacks; no-op canonical edits; detached input/output objects;
ownership and ordinary/rich transitions. Cover all five label styles, case, alphabetic boundaries,
Roman 3999/4000, zero/negative/signed extremes, nested RTL/LTR text/wrappers, checkbox normalization,
empty items' block arrays, and unchanged state/IDs/cursors/events after rejected input or edit.

Reject empty outer items, mixed orderedness, invalid types/scalars/ranges, missing blocks,
output-only labels, unknown fields and budget overflow. Test visible-content mutation boundaries
through public behavior; do not test only private helpers or derive expected labels using the
implementation. Source ambiguity goes to the coordinator before selecting invented behavior.

Use the assigned checkout's pinned shell/venv and outer network guard. Run focused rich world/API
tests and relevant lint/format; existing test files are not strict-typed, so do not silently widen
their unrelated typing scope. No full core or Android gate, APK build or guest is assigned.
Commit owned files and return exact red/green evidence, limits and a frozen clean branch. Leave
this ticket claimed until coordinator acceptance.
