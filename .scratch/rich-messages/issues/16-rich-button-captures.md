# Capture rich-button labels without confusing action metadata for visible text

Type: task
Status: ready-for-agent
Work state: open
Blocked by: ticket 14 for positive public execution

Follow the frozen [button contract](../../../docs/development/rich-buttons-contract.md).
Own src/gramlab/_captures.py, new tests/test_runner_rich_action_captures.py and this ticket.
Use a separate task branch/worktree. Do not change core normalization, native targeting, shared
fixtures, the public scenario API or global docs.

Extend readable-fragment traversal to inline text-button labels and row labels in document order,
including nested blocks and label arrays. Do not expose callback data, copied text, style or
alignment as capture text; preserve complete canonical history. Reuse the actual public runner
and real fixture bot for boundary checks, with independently authored input and expected output.
Include positive initial/edit/cold semantic capture and negative action-metadata/cross-button
fragment requests. Preserve existing fragment behavior and limits. This does not enable public
rich-button taps or prove per-button accessibility. Shared _rich_text callers must handle new
inline text without a KeyError.

Record the base failure honestly: core rejects new types until ticket 14 is integrated. Add a
focused traversal-specific failure only if it uses the actual Captures/World or public runner
boundary, without patching production validation or writing invented database state. Do not use
helper-only tests as the main acceptance. Run scoped Ruff/format/mypy and the focused public tests
under the pinned shell/outer network guard. Coordinator performs positive integrated checks after
the frozen core branch is merged. No guest, build or full gate is assigned. Commit only owned
files and return a clean frozen branch; keep the ticket claimed until combined acceptance.
