# Normalize rich callback, copy and disabled buttons

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none

Implement the frozen [button contract](../../../docs/development/rich-buttons-contract.md) in the
independent Python validator. Own src/gramlab/rich_messages.py, new tests/test_rich_actions.py,
new tests/test_rich_actions_api.py and this ticket. Other production files, old tests, global docs
and shared fixtures remain coordinator-owned. Use a separate task branch/worktree.

Establish World and real JSON/form HTTP failures on the base before implementation. Compare
complete independently authored responses/history/events/differences, detached outputs and reopened
state. Cover both row and inline placement, recursive containers, all supported actions/styles,
fill and explicit alignment, label/copy cleaning versus unchanged callback bytes, multi-byte
callback/copy limits, malformed/unknown/multiple action rejection and unchanged state after rejection.
Prove canonical no-op edits, existing budgets and cross-bot/message ownership. Reuse existing real
HTTP helpers where appropriate; expected values must not call production normalization.

No public scenario input, clipboard world model, native projection, renderer or network expansion
is assigned. New button labels/fields must be handled within existing aggregate limits. Follow
TESTING.md and parallel-work.md. Run the new focused World/API tests and source mypy plus scoped
Ruff/format in this checkout's provisioned offline environment under the outer network guard.
Coordinator owns full gates and integration. Commit only owned files, return frozen clean branch
and exact red/green evidence, and keep the ticket claimed until integrated acceptance.
