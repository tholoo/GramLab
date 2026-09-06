# Consistent agent worktrees and coordinator integration

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

Prepare concurrent implementation using separate task branches under a sibling worktree
container. The coordinator owns integration, conflict resolution and shared project records.
Preserve the independent Python simulator and actual Android renderer boundaries.

## Acceptance

- Worktree destinations stay under the same sibling container when invoked from any checkout.
- Worker entry checks reject the wrong checkout or branch before implementation.
- Dirty work, occupied paths and branches remain intact on rejected creation.
- Agents follow one linked assignment, ownership, verification and handoff procedure.
- Coordinator reviews and merges branches individually, resolves conflicts and validates the
  integrated result; workers report focused evidence instead of duplicating expensive gates.
- Exercise real disposable Git repositories and shared locks. Keep local paths and runtime
  evidence out of tracked instructions. Create the requested sibling container locally.

## Answer

The [workflow](../../../docs/development/parallel-work.md) defines assignments, file ownership,
worker commits, coordinator-only merges/conflict resolution, focused and combined checks, resource
locks and evidence-preserving cleanup. Root agent guidance points to it, and the tracker now
requires parallel workers to claim only their assigned ticket.

`tools/worktree` uses a stable sibling container from primary or linked checkouts, provides
`root` and `check NAME`, and rejects hidden untracked work and occupied/symlink containers or
destinations. The requested local container exists; actual paths remain outside tracked records.

Verification: the initial changed contract fails against the old placement/dirty-work behavior;
all 15 final `tests/test_developer_tooling.py` cases pass. Real Git tests cover explicit bases,
missing tickets at a selected base, wrong assignment/branch, dirty tracked/staged/untracked files,
occupied resources and shared lock contention/exit codes. A separate disposable two-worker smoke
exercise verifies branch commits, coordinator `--no-ff --no-commit` merges, both retained changes,
clean integration and removal after merge. Conflict resolution is documented, not exercised by
that clean-merge smoke. Bash syntax, ShellCheck, focused Ruff lint/format and local Markdown links
pass. Product behavior is unchanged; core/Android suites were not rerun for this tooling task.
