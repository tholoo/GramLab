# Verify two isolated Android test workers

Type: task
Status: ready-for-agent
Work state: claimed by coordinator
Blocked by: none

The serial native gate takes roughly 31 minutes. The existing pinned pytest-xdist dependency
may run independent tests concurrently without changing their guest CPU/memory, APK, snapshot
policy or runtime profile. Keep the entire invocation inside one foreground android-gate lock.

Read-only audit found that all 34 Android-selected test functions use tmp_path (parameterization
creates additional cases). Direct probes and public runner outputs have distinct host roots;
Sandbox supervisors create independent mount/PID/network namespaces and private home/cache/AVD
directories. Components share only their own enclosing test's network. Fixed emulator/ADB ports
therefore remain per-test. JDWP requests ephemeral ports and uses temporary class directories.
These are source findings, not concurrent guest proof.

First run one direct native probe and one public runner case together using -n 2 --dist=load,
with a fresh retained basetemp and the same read-only APK. Verify complete semantics, guest
isolation, original images, final process status and cleanup from both workers. If successful,
run the applicable full native gate once with the same worker count and frozen source/APK.
Retain JUnit suite time separately from summed case time and compare matched scope honestly.
Do not run builds or other guests during the pair or full gate. Local resource inventory stays
ignored. A timeout under parallel load requires diagnosis, including a serial reproduction
where justified; do not increase timeouts or weaken assertions to declare a speedup.

Coordinator owns scheduling, evidence, documentation and any resulting fixes. No production
profile change, renderer change, shared guest reuse, warm snapshot or network permission is assigned.
