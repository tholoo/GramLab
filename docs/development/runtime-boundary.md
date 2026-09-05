# Experimental Linux process boundary

Ticket 02 now has an independently written Python containment runner in
[`gramlab.runtime`](../../src/gramlab/runtime.py). It is an internal prototype interface, not
the public world/scenario API. The pinned Android tools and a dedicated AOSP guest now run through
it; no bot, simulator or Telegram client has. The [offline requirements](offline-safety.md) still
apply to those integrations.

## Provisioning and execution

The Linux development shells export `GRAMLAB_RUNTIME_PROFILE`, a Nix-generated JSON manifest.
It selects the pinned bubblewrap and Python executables and Python's immutable runtime closure.
The manifest and closure list are trusted provisioning inputs; do not accept them from scenarios,
clients or untrusted artifacts. The runner mounts individual closure entries read-only rather than
exposing the host's entire Nix store, home, runtime sockets or filesystem.

The Android shell additionally exports `GRAMLAB_ANDROID_RUNTIME_PROFILE`, including the SDK,
JDK and required shell utilities. Only this profile sets private Android home/cache locations
and a tool PATH inside the sandbox. Neither profile inherits the operator's proxy or credentials.

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
no physical devices are passed through by default. The explicit `kvm=True` option passes only
`/dev/kvm` for the approved virtual machine runtime. Namespace/mount failure never falls back to direct
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
.venv/bin/pytest -m 'not android' --cov=src/gramlab --cov-report=term-missing --cov-fail-under=80
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
DNS resolution policy, HTTP redirects/WebSockets, WebView/native/media paths, Telegram synthetic
activation, abrupt supervisor-death recovery, same-world concurrency and resource quotas remain
separate gates. The initial guest routing evidence is recorded below. No Telegram rendering,
Bot API compatibility or world persistence
claim follows from these tests. Store host-specific diagnostics in ignored local notes/artifacts.

## Dedicated Android guest evidence

Combined verification on 2026-09-06 passed all twelve tests with 90.65% statement coverage.
The core/probe type checks, lint/format, Nix/direnv/workflow checks and platform evaluation passed.

With the approved SDK already provisioned and KVM accessible, the optional Android gate is:

```sh
nix develop .#android
uv sync --locked
unshare --user --map-root-user --net bash -eu <<'BASH'
ip link set lo up
.venv/bin/pytest -m android
BASH
```

The tests skip explicitly when the Android profile or KVM is unavailable. The ordinary CI job
selects the core tests and does not claim Android coverage. To retain evidence, select a fresh
ignored path with pytest's `--basetemp=artifacts/<run-id>`; pytest removes an existing base path,
so never point this option at unrelated or still-needed artifacts.

The three Android tests verify the pinned emulator version in the private filesystem, default
KVM denial versus explicit API access, and creation/boot of a new account-free AOSP guest.
[`android_guest.py`](../../tests/probes/android_guest.py) runs entirely inside the boundary,
with its own ADB server, fixed emulator serial and new AVD. It retains tool/emulator logs, guest
properties/routes, a screenshot and the network outcomes in the run directory. No host ADB
server, personal device, account or pre-existing AVD is accessible.

The preparation profile uses emulator 37.1.11, AOSP API 36 default x86_64 revision 2, KVM,
SwiftShader, two virtual CPUs and 2048 MiB guest memory. The observed default display is 320×640
at 160 dpi. Audio, cameras, metrics and snapshots are disabled; DNS targets a documentation-only
address. These are guest preparation settings, not a Telegram fidelity/capture profile.
See the pinned [toolchain metadata](../../clients/android/toolchain.json) and Google's
[startup options](https://developer.android.com/studio/run/emulator-commandline).

The guest reports API 36, x86_64 and zero accounts. A real TCP exchange through guest alias
`10.0.2.2` reaches a service inside the run namespace. Guest TCP attempts to documentation-only
IPv4 and IPv6 destinations both exit with `Network is unreachable`; the emulator's containing
namespace has only `lo`. The captured display was inspected and shows the AOSP launcher.
This is narrower than proof for an adapted Telegram application's entire network surface.

Startup exposed a wrong command-line-tools path and missing sed/awk launcher dependencies;
the profile now selects the versioned path and declares those tools explicitly. The guest's
initial boot-complete property can precede network and launcher readiness, so the network probe
waits for the real local exchange with a bounded deadline. A timezone-data warning and modem
IPv6-loopback warning remain in emulator diagnostics; their effect on the future client has not
been established. No inherited host timezone/configuration was mounted to suppress them.
