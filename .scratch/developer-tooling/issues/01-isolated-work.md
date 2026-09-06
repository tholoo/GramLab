# Prepare isolated parallel development

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

The user authorized reusable developer tooling to support faster parallel work. Provide a small
local helper for ticket-bound sibling worktrees and a shared exclusive resource lock. Preserve
existing files and branches; do not publish, automatically merge, or copy local credentials.

## Acceptance

- Create a fresh task branch/worktree from a verified commit with a tracked ticket.
- Reject dirty starting trees, invalid names and missing tickets before mutation.
- Coordinate expensive checks across worktrees through an ignored local lock.
- Document ownership, integration and environment setup; exercise the helper against real Git.

## Answer

Implemented [tools/worktree](../../../tools/worktree) and the
[parallel development workflow](../../../docs/development/parallel-work.md). Creation preserves
existing work and pins a tracked ticket to a resolved base commit. Resource locks use common
Git metadata so linked worktrees contend without tracked machine state. No worker is spawned,
no remote operation occurs, and integration remains an explicit coordinator action.

Five real Git/lock tests pass in the outer network guard, including explicit-base isolation,
invalid setup with no branch creation, shared lock contention and child exit-code preservation.
Bash syntax, ShellCheck, Ruff and helper-test typing pass. CI checks the helper syntax and lint;
its behavioral tests join the existing core suite. No application behavior changes in this task.
