# Tests

`test_runtime.py` exercises real Linux processes: network/filesystem isolation, startup failures,
concurrent runs and descendant cleanup. Use the [runtime gate](../docs/development/runtime-boundary.md)
inside the Nix development shell; no Android infrastructure is needed for these tests.

`test_android_runtime.py` additionally validates the pinned emulator, explicit KVM access and
a fresh AOSP guest's boot/account state and local/external networking. It requires the Android
shell and KVM, and skips explicitly when they are unavailable. The trusted guest probe runs
inside the process boundary and keeps generated evidence in its isolated data directory.

Follow [TESTING.md](../TESTING.md) as implementation continues.
Test the simulator itself, consumers through its HTTP boundary, Android interaction/rendering,
and their agreement. Keep runtime artifacts outside committed fixtures.
