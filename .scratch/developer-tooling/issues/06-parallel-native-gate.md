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

## Trial evidence

The first pair completed in 100 seconds with the direct case passing and the public case failing
a host assertion: the real bot had already answered when native input returned. The documented
API permits that scheduling; complete retained results pass the corrected exact-answer assertion,
and an incorrect answer remains rejected. The corrected second pair passes the public case but
fails the direct case's initial cold launch: `Status: timeout`, followed by first display at
14.459 seconds in logcat. Its semantic phases subsequently complete; this does not make the launch
assertion pass. The second suite takes 132 seconds. The affected case passes alone in 75 seconds,
with the APK/profile/timeouts unchanged. This does not isolate the cause. Concurrent scheduling is not accepted yet; do
not infer reliability or a speedup from either trial. The full native gate remains pending.

The retained failed trial identifies a 58.073-second system report labelled
`UWB Bugreport: error enabling UWB`. Collection overlaps the 14.459-second initial display and
also a successful 9.080-second restart. Neither passing control's three retained log windows
contains report collection; this does not prove absence throughout boot. Probe scripts, profiles
and AVD settings match across trials, and every emulator log enables UWB streaming. The report's
original request/error is outside the retained 2,000-line brief-format tail, so neither its
underlying trigger nor its causal role in startup delay is established.

The next economical diagnostic is timestamped log capture from first ADB availability through
app startup during an already planned guest run. Preserve scheduling, profile and timeouts; do
not disable a platform feature from correlation alone. Record boot readiness separately from
total probe elapsed time: the current private `boot_seconds` field includes the extra probe and
final capture, so it cannot be used as a boot-only measurement.
