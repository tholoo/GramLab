# Android host feasibility

Observed 2026-09-05 for foundation ticket 01. These are capability probes, not an Android
runtime, simulator, or zero-egress certification. No bot, client, emulator or scenario was run.

## Host observations

| Probe | Observed result | Implication |
| --- | --- | --- |
| `uname -srmo` | Linux 7.2.0, x86_64 | Candidate x86_64 emulator host |
| `/proc/cpuinfo`, loaded modules | `svm`, `kvm_amd`, `kvm` | AMD virtualization present |
| Open `/dev/kvm`, `KVM_GET_API_VERSION` ioctl | Read/write access; API version 12 | Kernel API usable by current user; emulator boot still untested |
| Memory and project filesystem | About 29.2 GiB RAM and 168.7 GiB free | Start with one renderer; determine concurrency from measurement |
| Host command lookup | `adb`, `nix`, `unshare`, `ip`, `nft` available | Some preparation tools available |
| Host command lookup | `java`, `gradle`, `emulator`, `sdkmanager`, `avdmanager` absent from PATH | Build/runtime provisioning needed |
| SDK configuration | `ANDROID_HOME`, `ANDROID_SDK_ROOT`, `JAVA_HOME` unset; common SDK paths absent | No usable SDK identified; not an exhaustive filesystem inventory |
| `systemctl is-active waydroid-container.service libvirtd.service` | Both inactive | No evidence either service is required for the proposed emulator |
| `/dev/binder` | Absent | No Waydroid baseline established |
| Disposable user/network namespace | Created successfully | Candidate independent network boundary |

The command sandbox hid `/dev/kvm` and denied system bus/netlink access. Read-only host checks
and the disposable namespace probe were repeated outside it with automatic approval. The host
has working KVM access; do not request enabling KVM based on sandbox device visibility.
No NixOS configuration, host routes, firewall rules, services or group membership changed.
No ADB server was started and no personal devices or account directories were inspected.

## Reproducible capability probes

Read-only KVM query, outside a sandbox that hides the device:

```sh
python - <<'PY'
import fcntl
import os
fd = os.open('/dev/kvm', os.O_RDWR | os.O_CLOEXEC)
try:
    print(fcntl.ioctl(fd, 0xAE00, 0))  # KVM_GET_API_VERSION; observed 12
finally:
    os.close(fd)
PY
```

Disposable namespace probe, outside the command sandbox's netlink restriction:

```sh
unshare --user --map-root-user --net sh -eu -c '
  ip link set lo up
  ip -brief address
  ip route show
  ip -6 route show
  python - <<"PY"
import errno
import socket
with socket.socket() as listener:
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    with socket.create_connection(listener.getsockname(), timeout=1) as client:
        server, _ = listener.accept()
        with server:
            client.sendall(b"gramlab-probe")
            assert server.recv(64) == b"gramlab-probe"
for family, address in (
    (socket.AF_INET, ("192.0.2.1", 443)),
    (socket.AF_INET6, ("2001:db8::1", 443, 0, 0)),
):
    with socket.socket(family, socket.SOCK_STREAM) as connection:
        connection.settimeout(1)
        assert connection.connect_ex(address) == errno.ENETUNREACH
print("local TCP passed; IPv4 and IPv6 documentation ranges unreachable")
PY
'
```

Observed only `lo` with `127.0.0.1/8` and `::1/128`, no displayed routes, a successful local
payload exchange, and `ENETUNREACH` for both reserved documentation destinations. No real
Telegram destination was used. The namespace disappeared when its final process exited.
This checks the host mechanism with Python sockets; native transport, DNS, redirects,
WebSockets, WebView, media, background services and guest routing remain unverified.

## Runtime recommendation for review

Use a dedicated Android Emulator with an x86_64 AOSP image, KVM, and an explicit software GPU
backend initially. Pin image revision/checksum, emulator package revision, display density,
viewport, fonts, locales, theme and animation capture policy before producing fidelity evidence.
The current evidence does not select an exact image/emulator revision or certify any build.
Android documents KVM for Linux acceleration and explicit graphics backend selection; run the
installed emulator's `-accel-check` before the first boot.
[Android acceleration documentation](https://developer.android.com/studio/run/emulator-acceleration)

Provision a project-scoped tool environment separately from execution, with exact package
versions, hashes and license records. On NixOS, verify loader/native-library requirements before
promising that Google's downloaded SDK binaries will execute. No host service change is
currently justified. Installing system components or changing services requires a separate
concrete review if project-scoped provisioning proves insufficient.

Proposed execution boundary: put the simulator, bot, local fixture/Mini App servers, dedicated
ADB server and emulator in one fresh network namespace per run, with loopback only and no
veth, physical interface or default route. Network namespaces isolate interfaces, routes and
socket port spaces. This makes a namespace a plausible outer boundary; the probe above is
limited evidence of this host's support.
[Linux network namespace documentation](https://man7.org/linux/man-pages/man7/network_namespaces.7.html)

Also isolate mounts and process resources, clear inherited proxy settings and unnecessary file
descriptors, hide host sockets, expose only dedicated writable data and required runtime assets,
and drop namespace setup capabilities before running workloads. A network namespace alone does
not prevent escape through a host filesystem socket, inherited connection or shared host service.
Audit emulator routing and its DNS/host aliases against the actual pinned runtime; do not treat
an emulator alias as an allowlist. Headless runs should require no desktop sockets. Interactive
runs need a separately reviewed minimal display connection.

Require negative probes from the guest and each relevant runtime process, inspect namespace
membership/routes and packet counters independently, and test forbidden destinations without
allowing packets onto a host uplink. Enforce an application endpoint allowlist as well: a namespace
prevents external egress but does not authorize arbitrary local access. Dedicated ADB/control
listeners must not expose other worlds or attach personal devices. Startup must fail closed if
isolation cannot be established. These are proposal requirements, not implemented controls.

## Preparation verification

- Existing scaffold committed as `bec0ef4`; task branch `research/android-offline-seam`.
- `uv lock --check --offline` succeeded with a writable temporary cache.
- `uv sync --locked --offline` succeeded using the pre-existing host cache outside the sandbox;
  it installed 18 locked development packages without registry access.
- Ruff lint and format checks passed; configuration and all 32 initial Markdown files' local
  links validated. No Python implementation exists; pytest/mypy behavioral gates do not apply.
- An `origin` remote exists (`git@github.com:OWNER/GramLab.git`), contrary to the initial handoff.
  It was not fetched, pushed or otherwise queried. Publication remains unauthorized.
