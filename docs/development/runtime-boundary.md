# Experimental Linux process boundary

Ticket 02 now has an independently written Python containment runner in
[`gramlab.runtime`](../../src/gramlab/runtime.py). It is an internal prototype interface, not
the public world/scenario API. No bot, simulator, Android guest or Telegram client has yet run
through it. The [offline requirements](offline-safety.md) still apply to those integrations.

## Provisioning and execution

The Linux development shells export `GRAMLAB_RUNTIME_PROFILE`, a Nix-generated JSON manifest.
It selects the pinned bubblewrap and Python executables and Python's immutable runtime closure.
The manifest and closure list are trusted provisioning inputs; do not accept them from scenarios,
clients or untrusted artifacts. The runner mounts individual closure entries read-only rather than
exposing the host's entire Nix store, home, runtime sockets or filesystem.

`Sandbox(profile).run(command, data=directory, timeout=seconds)` accepts an argument vector and
an existing, dedicated data directory chosen by the trusted supervisor. That directory is the
only persistent writable mount, visible as `/work`. Callers must allocate private directories
and must not supply personal data, host sockets or shared directories. This layer does not yet
allocate world directories, serialize same-directory access or validate media/archive contents.
Paths are opened component by component without following symlinks; a directory descriptor pins
the final bind source across renames. Symlinks *inside* the run cannot reveal unmounted host paths.
The runner preserves artifacts and does not delete host directories.

Each invocation creates fresh user, mount, PID, network, IPC, UTS and cgroup namespaces. The
network has only a working loopback interface. Environment variables and inherited descriptors
are cleared, standard input is closed, capabilities are dropped, further user namespaces are
disabled and terminal sessions are separated. `/proc`, `/dev`, `/tmp` and `/run` are private;
no physical devices are passed through. Namespace/mount failure never falls back to direct
execution. The Linux kernel must support unprivileged namespaces and pidfds; failure is an error,
not unavailable coverage disguised as a pass.

Before releasing the startup gate, the supervisor opens a pidfd for the namespace init.
On completion, interruption or timeout it terminates that namespace and waits for kernel-confirmed
exit, including detached descendants. Early setup cleanup targets the launcher's still-owned
process group. Timeout raises `subprocess.TimeoutExpired`; other command failures return their
exit code and captured output. Cleanup failure raises an error. Output is captured in memory, so
this initial runner is for bounded preparation commands and probes; long-running reporting/log
retention and resource quotas remain work for the scenario supervisor.

The use of explicit flags follows the pinned
[bubblewrap security model](https://github.com/containers/bubblewrap/blob/v0.11.2/README.md).
Its [process implementation](https://github.com/containers/bubblewrap/blob/v0.11.2/bubblewrap.c)
distinguishes the launcher, namespace init and workload; launcher exit alone is insufficient to
establish completed cleanup. No client-derived code enters this implementation.

## Reproducing the behavioral gate

Provision dependencies first, then run the tests inside an additional disposable network
namespace. The tests verify that each child has a *different* namespace from this outer guard.

```sh
nix develop
uv sync --locked
unshare --user --map-root-user --net bash -eu <<'BASH'
ip link set lo up
.venv/bin/pytest --cov=src/gramlab --cov-report=term-missing --cov-fail-under=80
BASH
```

The manually dispatched CI runs the same gate in its Nix job. It must fail if the runner cannot
create namespaces; this repository does not silently change host security policy. macOS has a
development shell but no implementation of this Linux containment boundary.

## Evidence and limits

Verification on 2026-09-06: all nine tests passed, with 90.10% statement coverage. Strict mypy,
Ruff lint/format, configuration and local-link checks, Nix checks and all-platform evaluation
passed. The configured GitHub workflow has not been dispatched remotely.

The tests observe real processes and kernel state, without mocking process execution:

- Local TCP succeeds; a listening parent loopback service is unreachable from the child.
- IPv4/IPv6 TCP and IPv4 UDP attempts to documentation-only external addresses fail with
  `ENETUNREACH`; the child has only `lo` and a distinct network namespace.
- Parent files, inherited open descriptors and host home/runtime directories are unavailable.
  Owned artifacts persist. Kernel mount flags show read-only dependency mounts; writes fail.
- Effective capabilities are empty, no-new-privileges is enabled, and new user namespaces fail.
- Detached descendants release their lifetime locks before normal or timed-out runs return.
- Symlinked data roots are rejected before startup. Missing dependencies prevent startup.
- Two simultaneously live runs bind the same TCP port and retain independent data and namespaces.

The initial test failed because no Python package existed. Subsequent behavioral tests exposed
accepted symlinked data roots and a race between timeout return and detached-child teardown.
Both regressions passed after descriptor-based mounts and pidfd-supervised cleanup were added.
The permission test also checks mount flags because Linux may return `EACCES` before `EROFS`.

These observations establish the tested process boundary only. Application endpoint allowlists,
DNS resolution policy, HTTP redirects/WebSockets, emulator guest routing, WebView/native/media
paths, synthetic activation, abrupt supervisor-death recovery, same-world concurrency and resource
quotas remain separate gates. No Android rendering, Bot API compatibility or world persistence
claim follows from these tests. Store host-specific diagnostics in ignored local notes/artifacts.
