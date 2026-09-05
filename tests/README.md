# Tests

`test_runtime.py` exercises real Linux processes: network/filesystem isolation, startup failures,
concurrent runs and descendant cleanup. Use the [runtime gate](../docs/development/runtime-boundary.md)
inside the Nix development shell; no Android infrastructure is needed for these tests.

Follow [TESTING.md](../TESTING.md) as implementation continues.
Test the simulator itself, consumers through its HTTP boundary, Android interaction/rendering,
and their agreement. Keep runtime artifacts outside committed fixtures.
