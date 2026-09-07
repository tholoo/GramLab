# Match pinned rich-text cleaning before expanding rich actions

Type: bug
Status: ready-for-agent
Work state: claimed by rich-text-cleaning on task/rich-text-cleaning
Blocked by: none

The direct World boundary preserves a tab in a rich paragraph where the pinned TDLib
`RichText::get_rich_text` calls `clean_input_string` and produces a space. The coordinator's
complete-message comparison fails in 0.05 seconds; retained input, actual and expected output
stay in ignored artifacts. This is a canonical-state discrepancy, not an Android layout issue.

Worker ownership: src/gramlab/rich_messages.py, tests/test_rich_messages.py,
tests/test_rich_bot_api.py and this ticket. The coordinator
owns Android checks, shared docs and integration. Keep the code/APK under the current native gate
frozen; any implementation uses its own branch and worktree.

Follow [the reviewed contract](../../../docs/development/rich-text-cleaning.md) for all existing
RichText leaves and preformatted language. Keep the existing explicit rejection of other C0
controls and raw/canonical resource budgets. Avoid importing client implementation into the MIT
core. Record independently authored expected fixtures, including unaffected Persian/English,
ZWNJ/newline, tabs, removed Unicode controls/marks, runs of LRM/RLM, and multibyte boundaries.
Future button labels and copied text depend on the same source contract, but adding rich actions
or a new public input/geometry API is not part of this correction.

Implementation acceptance must cover complete World and real JSON/form HTTP send/edit responses,
durable history/events/differences/reopen, detached objects, normalized no-op edits, optional
plain-empty omission versus nested structure retention, and unchanged state after unsupported
input or budget overflow. Expected cleaning fixtures must not call the implementation. Review the
existing unrestricted Unicode-preservation property: normalization changes some accepted Unicode,
so preserve a valid unaffected-input property and separate source-derived transformation cases.
Do not increase its deadline or hide failures.

The reviewed boundaries and source-derived fixtures are committed before dispatch. Establish
tracked World/HTTP failing cases before fixing the validator. Run focused new normalization cases
inside the assigned pinned shell and outer network guard, plus scoped lint/format and source mypy.
Avoid the full rich suite's unrelated property case while the coordinator's Android gate is active;
report its deferred coverage, and retain all observed failures. No guest or build is assigned.
Commit only owned files and return a frozen clean branch with exact red/green evidence. Focused tests belong to the worker;
the coordinator retains the full combined gates and native normalization evidence. This correction
does not complete the rich-action or wider product inventory.

## Worker evidence

The tracked cleaning selection was replayed against the base validator after offline provisioning:
seven cases failed and the unaffected singleton/separated direction-marker case passed. Failures
covered recursive string cleaning, all four UTF-8 truncation boundaries and both real HTTP
encodings. With the correction applied, all eight selected cases pass. The combined focused
selection passes 30 cases, including the existing C0 rejection and raw/canonical resource-budget
checks. Scoped Ruff format/check and source mypy pass. The unrestricted property/full rich suite
remains deferred while the coordinator-owned Android gate runs, as assigned.
