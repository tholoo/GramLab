# Match pinned rich-text cleaning before expanding rich actions

Type: bug
Status: ready-for-agent
Work state: resolved after coordinator integration and acceptance
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

## Coordinator acceptance

Both frozen worker branches are merged. All 91 World/HTTP tests pass in 24.84 seconds, including
the previously deferred Unicode property. The independent real-bot regression passes in 1.01
seconds after its recorded failure on the old base. The full core gate passes 336 tests in 48.58
seconds with 80.67% coverage and no skips. Repository-wide lint/format, every documented strict
mypy scope, the Nix workflow check, offline package build, installed-wheel list scenario with
complete semantic verification, and installed World normalization verification pass.

The focused original-Android normalization test passes in 65.98 seconds using the existing APK.
It verifies complete native initial/edited serialization, live RTL editing, cold restart, applied
edit trace, successful launches, zero accounts and network/filesystem isolation. All three original
PNG captures were visually reviewed. Raw input, independent expected content, complete actual
observations, PNG/XML and HTML report remain in ignored artifacts. No Java, APK, renderer or
profile change was needed. The preceding full 38-case Android gate predates this correction;
focused native acceptance does not claim a full 39-case rerun. All checks are terminal.

Reproduce the native acceptance in the provisioned Android environment and documented outer
network guard, holding the shared `android-gate` lock, with
`pytest -m android tests/test_android_rich_cleaning.py`. The full core gate selects `-m 'not android' -n 4` with source coverage and its 80% floor in
the guarded pinned environment. Rich actions and the wider product inventory remain open.
