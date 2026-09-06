# Retain command-line development environments

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none

The user authorized reusable developer tooling. Repeated command-line development shells can
lose unrooted dependencies between runs, causing expensive provisioning before the next test.
Keep each worktree's selected shell rooted through a standard Nix profile under ignored cache
storage. Preserve the pinned flake and ordinary Nix argument/exit behavior; do not change host
garbage collection settings or weaken runtime containment.

## Acceptance

- Provide a small helper selecting only the existing default or Android shell.
- Retain its environment with `nix develop --profile` in ignored per-worktree storage.
- Verify actual shell execution and the resulting Nix root; check syntax, lint and invalid input.
- Document command-line usage alongside direnv and the shared Android gate lock.

## Answer

[tools/dev](../../../tools/dev) selects the existing flake shells and records them through
`nix develop --profile`. Profile paths are per-worktree and ignored; ordinary command arguments
and exit status pass through without evaluation. The [environment](../../../docs/development/environment.md)
and [parallel workflow](../../../docs/development/parallel-work.md) document its use.

Actual offline default-shell execution reports Python 3.13 and the registered persistent Nix
root. A real child exit status of 7 is preserved. Help and invalid-shell rejection, Bash syntax,
ShellCheck, all-platform flake evaluation and the three host-platform Nix checks pass. After
dependency restoration, the actual Android profile also registers its persistent root. Its closure
contains the restored ADB, AVD manager and emulator executables. That proves retained provisioning,
not Android behavior; runtime tests remain separate. Host settings and runtime containment are
unchanged.
