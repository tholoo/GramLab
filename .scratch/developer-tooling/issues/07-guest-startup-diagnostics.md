# Retain timestamped startup evidence without changing the guest profile

Type: task
Status: ready-for-agent
Work state: resolved
Blocked by: none for helper preparation; coordinator integration after current normal gate

The [parallel trial](06-parallel-native-gate.md) retained only a late, brief-format log tail. It
missed the initiating UWB/report request. The existing private `boot_seconds` field also includes
the entire extra probe and final capture, so it is not boot readiness. Prepare diagnostics for the
next already planned guest; do not rerun or change the current normal gate.

Worker owns tests/probes/android_guest.py, new tests/test_guest_startup_diagnostics.py and this
ticket. Prefer a small helper within the already staged android_guest.py so existing guest
launchers need no new staged dependency. Use a separate branch/worktree. Coordinator owns global
docs, all guests/builds, other probes and scheduling. No APK, emulator parameters, timeouts,
network/profile, renderer, retries or UWB setting changes are assigned.

Start timestamped system log observation as soon as the existing boot polling command first
successfully reaches ADB, retaining existing buffered early startup entries and streaming through
the extra probe. Bound retained output explicitly and retain the beginning rather than silently
replacing it with another late tail. Continue draining when capped so logging cannot block the
child. Keep selected startup/system tags (activity/window/input, UWB and bugreport/dumpstate paths)
and filter arbitrary app log tags; no credentials or bridge configuration may enter diagnostics.
Expose collection success/early exit/truncation/error explicitly. Logcat absence/failure must not
masquerade as complete startup evidence. Use fixed dedicated serial and argument arrays.

Stop/reap the owned logger and drain/close its reader on both successful and exceptional probe
exit before terminating the guest. Do not kill an unidentified ADB server or another run's process.
Retain useful partial evidence on a boot/probe failure. Keep added IO/retention bounded and the
existing guest/bot/network boundaries intact. Add explicit boot-readiness and probe-elapsed timing
observations; preserve and document the old misleading private field if retaining compatibility,
or record any rename and its verified consumers. Do not claim a startup cause from elapsed time.

Behavioral helper tests should exercise real controlled child processes that emit timestamped
sample output, overflow the byte cap, exit early and stay alive until cleanup. Verify no owned
process survives normal or exceptional context exit and retained bytes/status distinguish complete,
partial and truncated observation. This is process/collector evidence, not fake Android proof.
Do not mock normal World/guest behavior or launch an emulator in the worker. Run focused tests,
Ruff/format and strict typing in the pinned offline shell and outer network guard. Retain exact
red/green/cleanup evidence. Native applicability is coordinator-owned in the next planned guest.
Commit only owned files and hand back a frozen clean branch; keep the ticket claimed until
integrated process checks and actual guest observations pass.

## Worker evidence

The new process suite first failed at collection because no startup collector existed. All five
focused cases now pass with real controlled child processes: a live stream, bounded overflow,
natural early exit, launch failure and exceptional context exit. They verify exact beginning
retention, explicit status/truncation/error fields, continued draining and owned-process reaping.
The fixed command test covers the dedicated serial, timestamp format, system buffers, selected
system tags and final tag suppression. Scoped Ruff format/check and strict typing of the staged
probe pass. No emulator, guest, APK, build, network or shared gate was run; native applicability
and actual startup evidence remain coordinator-owned.

Review follow-up made failed extra probes retain their elapsed time, handles a process exit between
the final poll and termination, and asserts reader shutdown after normal and exceptional cleanup.
The overflow emitter now writes 8 MiB and creates a separate completion marker before cleanup,
proving the collector drains beyond pipe capacity after its retained prefix is full. Retained boot
logs showed `UwbServiceCore`, `UwbSettingsStore`, `UwbCountryCode`, `UwbContext`, `uwb` and hardware
UWB tags, which were added to the finite system allowlist. The focused suite and scoped Ruff and
strict typing checks, including the new test file, pass after the follow-up.

## Timing and observation semantics

`startup_log_started_seconds` measures the first successful existing ADB boot poll from guest
launch; `boot_ready_seconds` measures observed `sys.boot_completed=1`. `extra_probe_seconds`
measures only the supplied extra probe and survives its exception. The retained legacy
`boot_seconds` is total probe elapsed time, including setup, extra probe and final capture; it is
not boot readiness. `startup_log` records a bounded prefix and explicit collection outcome.
A `complete` collector outcome means the owned stream stayed alive until intentional cleanup;
it does not prove that every boot event was logged or identify a startup cause. Actual guest
log format, buffering, tags and cleanup remain pending the coordinator's planned native trial.

## Integrated native acceptance

The five controlled-process cases pass after integration in 0.27 seconds. Actual failed and
successful native probes retain timestamped buffered startup logs, separate boot/probe timing,
explicit untruncated collection and a reaped logger. The failed scene-predicate trial retains
141,101 bytes and its partial timing observations; the successful two-callback/edit/restart trial
retains 65,832 bytes. These are bounded collector observations, not complete Android log coverage.
The existing normal rich-message and cleaning probes also pass after integration (two cases in
169.61 seconds). All 390 cases in the combined core gate pass at 80.99% coverage.

The early failed-trial log identifies UWB initialization timeout and a failed retry, followed by
a full system report request from the same system thread. The successful input control initializes
UWB successfully and contains no report collection in its untruncated observed interval. Both app
launches succeed. This identifies the report requester in one run; it does not establish the cause
of intermittent UWB initialization failure or a causal contribution to launch latency. Parallel
Android scheduling remains unaccepted and the guest profile/timeouts are unchanged.
