# Tests

`test_runtime.py` exercises real Linux processes: network/filesystem isolation, startup failures,
concurrent runs and descendant cleanup. Use the [runtime gate](../docs/development/runtime-boundary.md)
inside the Nix development shell; no Android infrastructure is needed for these tests.

`test_android_runtime.py` additionally validates the pinned emulator, explicit KVM access and
a fresh AOSP guest's boot/account state and local/external networking. It requires the Android
shell and KVM, and skips explicitly when they are unavailable. The trusted guest probe runs
inside the process boundary and keeps generated evidence in its isolated data directory.
With `GRAMLAB_ANDROID_PROBE_APK` selecting the built guarded APK, it also runs the real
[JNI guard probe](../docs/development/android-native-guard.md) through guest `app_process`.
That probe does not install or start the client application.

`test_android_client_bridge.py` connects a separate bot process and authoritative world to the
Android semantic adapter in a fresh guest. It checks the pinned client's serialized TL projection
and actual HTTP rejection cases. This still precedes application lifecycle and rendering evidence.

`test_world.py` checks persisted synthetic state and concurrent transitions. `test_bot_api.py`
exercises actual HTTP, including a separate bot process. `test_client_bridge.py` covers atomic
persona snapshots, journal cursors, storage migration and authenticated HTTP reads. Run them in
the outer network guard; these contracts do not establish Android rendering fidelity.

Follow [TESTING.md](../TESTING.md) as implementation continues.
Test the simulator itself, consumers through its HTTP boundary, Android interaction/rendering,
and their agreement. Keep runtime artifacts outside committed fixtures.
