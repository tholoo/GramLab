# Android host readiness

These portable checks help prepare an isolated Android environment. Store actual host inventory,
proxy addresses, local paths and probe logs in ignored `.cache/local-notes/` or `artifacts/`.
They are not part of the public repository or a renderer/isolation certificate.

## Requirements

The initial Android profile targets x86_64 Linux with usable KVM. Check available RAM and disk
before provisioning and begin with one renderer. The development flake provides project toolchains;
no Waydroid or virtualization service is assumed.

An execution sandbox may hide host devices or restrict netlink operations. Distinguish those
restrictions from missing host capabilities before proposing any system configuration change.
Never attach personal devices or reuse account data while checking readiness.

## Reproducible capability probes

Read-only KVM query, outside a sandbox that hides the device:

```sh
python - <<'PY'
import fcntl
import os
fd = os.open('/dev/kvm', os.O_RDWR | os.O_CLOEXEC)
try:
    print(fcntl.ioctl(fd, 0xAE00, 0))  # KVM_GET_API_VERSION
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

Expected result: only loopback addresses/routes, a successful local payload exchange, and
`ENETUNREACH` for both documentation destinations. The namespace disappears when its last process
exits. This checks the host mechanism with Python sockets; it does not verify Android native
transport, DNS, redirects, WebSockets, WebView, media or background services.

## Runtime recommendation for review

Use a dedicated Android Emulator with an x86_64 AOSP image, KVM, and an explicit software GPU
backend initially. Pin image revision/checksum, emulator package revision, display density,
viewport, fonts, locales, theme and animation capture policy before producing fidelity evidence.
Exact package versions belong in the committed toolchain profile; successful package acquisition
and actual emulator boot remain separate verification gates.
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
socket port spaces. This makes a namespace a plausible outer boundary; use the probe above
to test a prospective host before provisioning.
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
