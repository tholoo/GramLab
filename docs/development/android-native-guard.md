# Native transport guard

The second [Android patch](../../clients/android/patches/README.md) adds a compile-time
`GRAMLAB_OFFLINE` guard to the selected GramLab build. The application remains disabled while
startup, background networking and the Java semantic adapter are implemented.

## Boundaries

The shared Gradle module supplies `-DGRAMLAB_OFFLINE=ON`. CMake defines the guard on both the
JNI library and its `tgnet` static library. JNI `native_sendRequest` and `native_init` throw
`IllegalStateException("GRAMLAB_NATIVE_TRANSPORT_DISABLED")` before inspecting incoming pointers,
allocating requests or initializing transport. Native callers bypassing JNI encounter abort
backstops at `ConnectionsManager::init` and `ConnectionSocket::openConnection`, before creating
the worker or opening a socket. These backstops terminate on an invariant violation; they do not
pretend that a network operation succeeded.

JNI method registration and declarations are preserved. The existing `native_setJava(false)`
initializes memory/delegate support without starting the transport worker. Rendering/storage
buffer operations must remain available when transport is disabled. The independent
[OS boundary](runtime-boundary.md) remains mandatory; this patch is not a complete network policy.

## Guest probe

The GPL patch includes `org.telegram.tgnet.NativeGuardProbe`, an `app_process` entry point with no
manifest component. The Python orchestration pushes the APK and its real x86_64 native library
into a fresh [AOSP guest](android-runtime-provenance.md), then loads them through ART. It does not
install the package, invoke `ApplicationLoader`, or activate an account.

The request probe passes an opaque null pointer before `native_init`. In the pinned unguarded
source, this only queues a task: the transport worker has not been started and never consumes
the pointer. That baseline returned normally with a failing test result. The guard must reject
before any pointer handling. The initialization probe uses null metadata, which an unguarded
JNI path cannot consume before transport initialization. A separate native buffer round trip
checks that the JNI memory path still works.

After the [contained build](android-build.md), run the Android gate in its outer network guard:

```sh
nix develop .#android
export GRAMLAB_ANDROID_PROBE_APK=.cache/android-build/offline/source/TMessagesProj_GramLab/build/outputs/apk/debug/TMessagesProj_GramLab-debug.apk
unshare --user --map-root-user --net bash -eu <<'BASH'
ip link set lo up
.venv/bin/pytest tests/test_android_runtime.py --basetemp=artifacts/native-guard-01
BASH
```

Choose a fresh ignored artifact directory; pytest removes an existing base directory. The probe
requires the Android runtime profile, the explicitly selected APK and accessible KVM. Missing
prerequisites produce an explicit skip, which is unavailable coverage rather than proof. Retain
`guest.json`, `native-probe.log`, guest logcat and the emulator log. Host paths, local keys and
machine diagnostics stay ignored.

## Evidence limits

The regression directly exercises the real JNI request boundary. It does not directly invoke
the native abort backstops or prove every networking surface is disabled. VoIP, media, Java DNS,
push, WebViews, startup providers and account synchronization require separate treatment before
client activation. The existing guest network checks cover local reachability and denied external
IPv4/IPv6 attempts; they do not establish actual Telegram rendering, callbacks or recovery.

The first two development probes stopped before the request boundary because JNI memory setup
had not run. Those were setup failures, not evidence for the request guard. The corrected probe
reached JNI and returned `blocked=false` with exit 2 before the guard was applied.

Verification on 2026-09-06: the guarded APK returns
`{"request_blocked":true,"initialization_blocked":true,"buffer_round_trip":true}` with exit 0
and no stderr. All five Android runtime tests pass, including the unchanged guest/startup/KVM
checks. The probe guest has only loopback on its host side, reaches the local service and rejects
external IPv4/IPv6 attempts with `Network is unreachable`. Its captured screen is the AOSP launcher;
no Telegram UI was shown. A fresh pinned export applies both patches, matches all changed build
inputs and preserves the 6,666 checked upstream UI/resource files. Static, Nix/workflow and
public-tree privacy checks pass. No remote workflow or artifact publication occurred.
