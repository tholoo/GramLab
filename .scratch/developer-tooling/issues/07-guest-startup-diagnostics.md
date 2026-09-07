# Retain timestamped startup evidence without changing the guest profile

Type: task
Status: ready-for-agent
Work state: open
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
