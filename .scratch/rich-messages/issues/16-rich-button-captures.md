# Capture rich-button labels without confusing action metadata for visible text

Type: task
Status: ready-for-agent
Work state: resolved after coordinator integration and core acceptance
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

## Worker evidence

The capture walker now treats each rich button-row label as its own readable fragment and includes
an inline button label within its surrounding RichText fragment. It reads only button `text`, so
callback payloads, copied text, style and row alignment do not become capture evidence. The public
runner test uses a real standard-library HTTP bot and independently authored complete initial,
edited and repeated semantic capture expectations. It also rejects payload, copied-text, style,
alignment and cross-button targets while requiring string/array labels in both placements.

On the assigned base, the focused loopback-only public test fails before capture exactly because
`sendRichMessage` returns `GRAMLAB_UNSUPPORTED: rich content fields`. No validator patch, direct
World insertion or database fixture bypasses that expected ticket-14 dependency. Scoped Ruff
lint/format and strict mypy pass for both owned Python files. Positive public execution remains
coordinator-owned after integrating the core branch. No guest, APK build, full gate or external
network access was used.


## Coordinator acceptance

The frozen branch is merged. Integrated World/HTTP rich-button checks pass all 31 cases in
3.67 seconds, and the real public runner capture check passes in 1.28 seconds with complete
initial/edit/repeated histories and rejected action metadata. The combined core gate passes
368 tests in 49.71 seconds at 80.99% coverage. All documented static scopes pass. Native codec,
rendering and input are separately tracked; this ticket does not claim those outcomes.
