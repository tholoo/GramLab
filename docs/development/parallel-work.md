# Parallel development

Independent implementation can use separate branches and sibling Git worktrees. No application
architecture change or agent framework is needed. One coordinator owns integration and the shared
handoff; each worker owns a bounded ticket, its implementation files and dedicated tests. Agree
on shared interfaces before splitting work. Request interface changes through the coordinator
instead of editing another worker's files.

Start from a clean, verified commit containing the work tickets:

```sh
tools/worktree create native-input .scratch/programmatic-scenarios/issues/02-consumer-runner.md
tools/worktree list
```

The helper creates a sibling checkout and `task/native-input` branch, resolves the base to an
exact commit, and rejects dirty checkouts, existing destinations/branches and absent tickets.
An optional third argument selects another committed base. Claim the assigned ticket in the new
checkout before implementation and record the owned files and expected handoff. The helper
neither assigns workers nor merges their work. Do not assign one ticket to multiple workers.

Enter each checkout's Nix shell and run `uv sync --locked`. The existing shell keeps `.venv`,
caches and artifacts separate per checkout. Local environment overrides and credentials are
not copied. Provision dependencies through the approved workflow; normal execution still uses
the [offline guard](offline-safety.md). Nix store inputs can be shared as immutable resources.
Keep large writable Android builds and AVDs separate; reuse a verified APK only as an explicit
read-only input. Do not share writable virtual environments or Gradle homes.

Use a repository-wide resource lock for expensive Android gates:

```sh
tools/worktree lock android-gate nix develop .#android --command \
  unshare --user --map-root-user --net bash -eu -c \
  'ip link set lo up; .venv/bin/pytest -m android'
```

Provision the documented Android inputs before invoking that command. The wrapper preserves the
command's arguments and exit code. A busy resource exits 75 without running the command. Locks
live under the common Git directory, so all linked worktrees coordinate without recording local
paths or process metadata in tracked files. Locking requires Linux `flock`; the underlying runner
still provides actual containment. All workers must opt into the same resource name. Keep the
wrapped command in the foreground until cleanup completes; a detached process can retain its
inherited lock. Different repositories have independent locks.

At handoff, each worker commits its bounded change and reports the commit, owned files, tests,
artifacts and remaining concerns. The coordinator reviews and integrates those commits one at a
time, reconciles shared docs and runs the combined gates. Worker test results cannot establish
that the integrated tree passes. Worktree removal is a separate explicit Git action after changes
and evidence have been preserved; the helper never deletes branches or directories.
