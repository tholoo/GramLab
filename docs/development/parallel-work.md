# Parallel development

Each implementation worker owns one ticket, one `task/NAME` branch and one worktree. The
coordinator owns assignments, review, merges, conflict resolution and verification of the combined
result. Read-only research or review agents may inspect the shared checkout without creating a
branch; they must not edit it. This workflow keeps the independent Python simulator and original
Android rendering boundaries unchanged.

## Coordinator: assign independent work

1. Split the next milestone into bounded tickets with explicit acceptance criteria, owned files,
   dependencies and focused checks. Agree shared interfaces before implementation. Assign separate
   modules or layers with stable contracts; serialize tasks that require the same core files.
2. Commit the tickets and interface agreements on the clean integration branch. Record its exact
   commit as the base. Keep the global handoff, compatibility matrix, root agent guidance, lockfiles
   and shared architecture records coordinator-owned unless explicitly delegated to one worker.
3. Create each worker checkout using the assigned ticket, name and base:

   ```sh
   tools/worktree create NAME TICKET BASE
   tools/worktree root
   tools/worktree list
   ```

   Substitute the assignment values. The helper creates `<primary-checkout>-worktrees/NAME`
   alongside the primary checkout, with branch `task/NAME`. For a checkout named `GramLab`, the
   container is `GramLab-worktrees`. The destination is stable from every linked worktree.
   Existing paths/branches and dirty starting checkouts are rejected. Tickets must exist at BASE.
4. Spawn the worker with the assignment below, including the absolute checkout path discovered
   locally. A spawned agent can inherit the coordinator's working directory; creating a worktree
   alone does not put the agent there. Keep actual paths, process handles and artifact locations
   in the dispatch message or ignored local notes, rather than committed tickets.

Use this dispatch template; fill every field before delegating implementation:

```text
Role: implementation worker; coordinator owns integration.
Task name / branch: NAME / task/NAME
Assigned checkout: locally resolved absolute path
Base commit: exact commit
Ticket: repo-relative path
Owned files: explicit paths or bounded directories, including tests and task-specific docs
Shared interfaces: agreed contract and dependencies
Acceptance: observable outcomes and rejected cases
Verification: focused commands and required resource locks
Read AGENTS.md, docs/development/handoff.md, your ticket and this workflow.
Use the assigned checkout as workdir for every shell call and absolute paths for file edits.
Run tools/worktree check NAME before edits and after resuming a turn.
Commit only your assigned changes, then send the handoff below. Do not merge other branches.
```

Keep one coordinator slot available. Start a worker only when it can make useful progress without
waiting on another worker's unfinished interface. Report blockers promptly so the coordinator can
reassign work. Creating more branches is not a substitute for resolving a shared dependency.

## Worker: implement and hand back

1. In the assigned checkout, run `tools/worktree check NAME`, inspect Git status and confirm the
   assigned base is an ancestor of HEAD. Claim only your assigned ticket. Record ownership and
   acceptance in that ticket before implementing; keep it claimed until integration succeeds.
2. Use this checkout's `tools/dev` and pinned environment. `tools/dev` selects the checkout that
   contains the script, so calling the primary checkout's helper would enter the wrong checkout.
   Provision with `tools/dev default --command uv sync --locked` from this checkout; use the
   explicit workdir on every tool call. The shell sets `UV_PROJECT_ENVIRONMENT` to its own `.venv`.
   A worker can inherit the coordinator's `UV_PROJECT_ENVIRONMENT`; changing directories alone
   does not change that target. Never run bare `uv sync` against an inherited target. If a separate
   temporary environment is required, set its target explicitly and verify the imported
   `gramlab.__file__` resolves to this checkout before reporting any checks.
   Keep `.venv`, Gradle homes, writable Android builds, AVDs and artifacts separate. Immutable Nix
   store inputs and an explicitly verified read-only APK may be shared. Copy no credentials or
   private consumer configuration into task branches.
3. Implement the assigned acceptance criteria following [TESTING.md](../../TESTING.md). Request
   shared interface or ownership changes from the coordinator before editing another task's files.
   Report required shared-doc changes in the handoff. The offline and licensing requirements still
   apply; dependency provisioning is separate from runtime network access.
4. Run focused checks and any explicitly assigned integration check. Preserve failures and report
   unavailable coverage honestly. Stop task-owned processes and complete cleanup before releasing
   resource locks. Review the diff and commit only owned files on `task/NAME`.
5. Send the structured handoff below. Keep the branch stable after handoff; further edits require
   a coordinator follow-up, with a new commit and updated evidence. The coordinator integrates it.

```text
Task / branch / base / final commit:
Owned files changed:
Acceptance outcomes:
Checks: exact commands, pass/fail/unavailable, meaningful counts and failure explanations
Evidence: ignored artifact paths plus portable reproduction details
Shared-doc updates for coordinator:
Remaining gaps, interface changes or integration risks:
Processes/resources: terminal and cleaned, or explicitly identified remaining work
Git state: clean, or explained uncommitted files
```

## Shared resource locks

All Android guest suites use the common `android-gate` lock. Android builds use `android-build`.
Builds and guests still need their own writable directories. Provision the documented inputs
before running a gate, and invoke it from the assigned checkout:

```sh
tools/worktree lock android-gate tools/dev android --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -m android'
```

This is the full Android gate; workers normally run the smaller scope in their assignment. The
[offline guard](offline-safety.md) remains mandatory. Locks live in the common Git directory,
coordinate all linked worktrees, and preserve command arguments and exit status. A busy lock
exits 75 without running the command: do useful independent work or report the contention. Keep
commands in the foreground through cleanup; a detached child can retain its inherited lock.
Locks coordinate resource use, not filesystem permissions or runtime containment.

## Coordinator: review and integrate

1. Verify the worker's final commit, clean checkout, completed processes and acceptance evidence.
   Review `git diff BASE..COMMIT` and the commit list for scope, tests, provenance and ownership.
   Compare the branch tip with the handed-off commit before merging. Return incomplete work to
   the same worker with a bounded follow-up.
2. From the clean primary integration checkout, merge one reviewed branch at a time with
   `git merge --no-ff --no-commit task/NAME`. Integrate only a frozen branch whose tip was reviewed.
   Use this approach consistently so task commits and merge boundaries remain visible.
3. Resolve conflicts in the integration checkout. Read both intended behaviors and their tests;
   preserve the agreed interfaces and acceptance criteria. Consult the worker for missing intent,
   and consult the user for consequential design changes under AGENTS.md. If integration must be
   deferred, `git merge --abort` restores the clean pre-merge state and retains the task branch.
4. Run affected checks on the merged index/worktree, reconcile coordinator-owned docs, and commit
   the merge with the task and relevant validation. Keep a failing merge under investigation rather
   than representing worker-only checks as integrated evidence. After the batch, run the applicable
   combined gate once; additional changes or failures justify another run.
5. Mark integrated tickets resolved only when their acceptance and required checks pass. Update the
   handoff and compatibility evidence. Preserve screenshots/logs needed for review outside the
   disposable worktree before removing it. Remove clean, completed worktrees explicitly with
   `git worktree remove`; retain task branches until evidence and reachability are confirmed.

Local commits and coordinator merges are authorized for this workflow. Remote publication remains
subject to user approval. Worktree cleanup must preserve uncommitted or ignored evidence; neither
the helper nor a worker automatically removes branches or directories.
