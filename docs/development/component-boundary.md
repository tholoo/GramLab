# Private runtime components on an isolated run network

The [runtime boundary](runtime-boundary.md) now distinguishes trusted orchestration from bot
execution. Real bot fixtures run in their own filesystem and PID namespaces while reaching the
world's authenticated HTTP service through the enclosing run's loopback network. Their writable
state persists separately from the world database and Android artifacts.

This extends the approved per-run namespace/mount direction; it is an internal foundation API.
The world services, fixture preparation and ADB orchestration remain trusted. The emulator host
process now has its own component mount and PID namespace, separate from the world and bots.
Resource quotas and general untrusted scenario packaging remain open.

## Execution contract

`Sandbox(profile).run(...)` retains its existing restricted behavior: a new offline network,
private mounts/processes, cleared environment/descriptors, no effective capabilities and no
further user namespaces.

`Sandbox(profile).supervise(command, data=directory, timeout=seconds)` starts **trusted**
orchestration with its own fresh offline network and the same outer filesystem/process guards.
It permits nested user namespaces so the supervisor can create restricted components. The
supervisor uses a fixed non-root UID/GID within that namespace and drops all effective
capabilities. The identity is internal to the namespace, not an operator's host account.

The non-root mapping avoids retaining `CAP_SETFCAP` to create further mappings of parent UID 0.
Linux has additional permission rules for that mapping since 5.12; see
[user namespaces](https://man7.org/linux/man-pages/man7/user_namespaces.7.html).
No subordinate host accounts, service changes or elevated host daemon are required.

Inside that supervisor, `Sandbox(profile).component(command, data=directory, environment=values)`
is a context manager yielding an interactive process. The child receives its own `/work`, private
PID/mount/user/IPC/UTS/cgroup namespaces, private `/proc`, `/dev`, `/tmp` and `/run`, and its
profile's read-only dependency closure. It inherits the run's network rather than creating a
disconnected second network. It receives only profile defaults and explicitly selected environment
values, never the supervisor's inherited environment or open descriptors. No KVM device is
exposed to bot components.

The explicit `kvm=True` component option exposes only `/dev/kvm`, for the approved emulator.
Both the outer supervisor and the selected component must opt in. An outer KVM device does not
automatically appear in children; requesting one when the outer runtime omitted it fails setup
without executing the component command.

The component path still uses descriptor-based, symlink-rejecting data-root selection. The
supervisor must select dedicated directories with appropriate contents; namespace isolation does
not make deliberately supplied host sockets, sensitive files or shared inodes safe. Fixture code
is copied once into a new bot directory before launch. Restart reuses that private directory and
does not follow bot-created symlinks while reinstalling files.

A reserved namespace marker and loopback-only check catch accidental component use outside the
supervisor. This is a misuse guard, not an authorization credential. Kernel-enforced mounts,
process separation, dropped capabilities and disabled further user namespaces protect the child
boundary. The provisioned closure now includes pinned bubblewrap and its dependencies so nested
setup does not depend on host executable paths or downloads.

## Lifetime and failure

Component startup is bounded by `startup_timeout`. The caller must bound interactive reads and
writes; the enclosing supervisor's timeout bounds the whole run. A pidfd pins each component's
namespace init before the startup gate opens. Leaving the context kills and waits for the entire
namespace, including children which detached into another session. Normal exit, exceptions and
explicit process kills take this cleanup path. Outer supervisor death or timeout also terminates
the complete run hierarchy. Failed setup never executes a workload directly as a fallback.

The callback fixture is killed after receiving its query and before changing world state. Its
second launch uses the same private directory, observes the pending query again, edits, answers
and acknowledges. A private launch counter reaches two; the bot refuses to start if it can see
the authoritative world's directory through `/work` or its namespace init's root.

## Evidence and remaining work

[`test_components.py`](../../tests/test_components.py) observes real processes and kernel state:

- The component reaches a local run service and writes persistent private state; supervisor
  files, escape symlinks and inherited descriptors remain unreadable.
- Component and supervisor share a network namespace, with external traffic rejected. Their
  PID namespaces differ; child capabilities are empty and further user namespace creation fails.
- Two components are simultaneously live, use distinct PID namespaces and update separate state.
- Normal exit, a raised exception, explicit kill, supervisor SIGKILL and timeout release a detached
  descendant's lifetime lock before the relevant context/run returns.
- Direct component launch outside trusted run orchestration is rejected before workload startup.

The initial contract failed because no supervisor/component API existed. Its first implementation
then failed closed at the nested UID mapping; a fixed non-root supervisor identity allowed setup
without retaining privileges. The real callback bot's new filesystem check failed under the old
shared-mount launch, then passed after migration to a private component. HTTP responses, callback
identity, message history and bot/client recovery assertions remain required.

Verification on 2026-09-06 passes 42 core tests at 90.64% statement coverage and all eight
Android tests. The Android callback case retains real input, visible editing and client restart,
and verifies two launches of the same private bot state. All earlier network/JNI/identity
rejections remain in the gate. Python lint/format and strict typing, Nix/direnv/workflow checks
and platform evaluation pass. The Android source, patch queue and tested APK are unchanged.

Run the core and Android gates using [CONTRIBUTING.md](../../CONTRIBUTING.md) and the outer network
guard in [runtime-boundary.md](runtime-boundary.md). Generated profiles, traces, private bot state,
guest data and screenshots belong in ignored run artifacts. No machine inventory or credentials
belong in this public record.

Same-run components share network reachability; authenticated service capabilities still govern
world/persona access. There is no per-port firewall or CPU/memory/disk/output quota yet. Bots can
still consume resources or disrupt services they can reach. Media/archive validation, WebViews
and broader application network surfaces remain separate gates.
This milestone does not close ticket 02 or establish complete hostile-workload containment.

## Emulator filesystem follow-up

[`emulator_process.py`](../../tests/probes/emulator_process.py) creates the AVD and executes the
pinned emulator inside a new private `emulator/` component directory. Its Android home/cache,
AVD, startup logs and emulator log remain there. The enclosing trusted probe keeps its own ADB
home and writes scenario evidence outside that directory. The guest still reaches world services
on the enclosing offline run network. SDK/image/graphics/display inputs are unchanged.

The regression observes the running QEMU process's actual root and namespace links through
the trusted supervisor's `/proc`. Before separation, world and bot sentinel files were visible
and QEMU shared the supervisor's PID namespace. With the component, its AVD remains visible but
world/bot paths are absent, its PID namespace differs and its network namespace remains shared.
The callback test repeats the observation after the real world and private bot state exist.
This tests the active emulator process rather than inferring isolation from launcher arguments.

Component cleanup uses the existing pidfd lifecycle, including emulator descendants. Normal
probe teardown terminates the component launcher and then waits for namespace cleanup. Logs are
written directly inside the private directory rather than accumulating emulator output in a pipe;
disk/output quotas are still absent. ADB, world services and artifact interpretation remain trusted.
Same-run ports, including emulator control and ADB, are not separated by a per-component firewall.

Follow-up verification on 2026-09-06 passes all ten Android tests, including both nested KVM
opt-in cases and the actual callback/edit/bot-and-client restart. The inspected edit/restart
screenshots preserve the expected mixed-language conversation. All 42 core tests still pass at
90.64% statement coverage. Ruff, strict typing, Nix platform evaluation and local checks pass.
The APK and upstream patch queue are unchanged; this milestone required no Android rebuild.
