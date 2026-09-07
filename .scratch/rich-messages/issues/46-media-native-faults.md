# Verify original photo download failures and recovery

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: reviewed APK for coordinator execution

Own new `tests/probes/android_media_faults.py`, `tests/test_android_media_faults.py`, this ticket,
and bounded extensions to `tests/probes/media_transfer_server.py` with its existing fixture tests.
Coordinator owns all guest/build execution, native patches, integration and shared docs.

Author a contained original-app acceptance scenario for truncated, corrupt, redirected and missing
photo responses using the existing controlled server. Require observed local failure, no readable
final photo or abandoned temporary file, then explicitly enable a complete response and cold-start
the same app to retry. Compare actual downloaded bytes and original screenshots after recovery.
Do not accept a failure solely because the server sent it, prefill a cache, or let an unplanned
automatic complete response hide a failed transfer. Extend the fixture with a controlled default
fault if required, and behaviorally test its real HTTP semantics under the outer network guard.

Keep each fault's app/cache state independent. One fresh dedicated guest may install once and
clear only this fixture application's data between fault cases. Capture both internal and
app-owned external storage, as selected by original AndroidUtilities/ImageLoader, and quote paths
passed through the remote shell. Existing native diagnostics are capability-free and identify
asset IDs, filenames, byte counts and terminal outcomes. Preserve all failed artifacts and the
ordinary account/isolation checks. Record every observed request; unexpected successful retries
must fail acceptance. Use explicit controlled events for transfer scheduling, with bounded waits.

Use the frozen v3 media contract and independently specified messages/assets. Normal photo
projection preserves asset/volume ID and local ID 1 through original serialization as of patch
0018. This task covers these four response faults and restart retry; concurrent cancellation,
duplicate attempts and late completion after live edit remain separate required coverage.
Author scoped tests/probes, run Ruff/format/mypy and HTTP fixture checks, but no guest/build.
Follow AGENTS.md, handoff, TESTING.md, offline safety and the parallel workflow. Return a frozen
clean commit, exact static/fixture results, known runtime limitations and terminal resources.

## Worker evidence

The controlled server now accepts a thread-safe default fault; unplanned requests keep receiving
that response until the test explicitly enables `complete`. Its real loopback HTTP checks pass,
including two consecutive default-missing responses followed by one explicitly enabled complete
response.

The original-app probe is authored for independent truncate, corrupt, redirect and missing cases.
It installs once, clears only the fixture app between Worlds, requires an actual native failure,
inventories internal and dedicated external app storage for final/temporary bytes, captures original
PNG/XML, then enables complete delivery and cold-starts recovery. Every ADB command retains stdout,
stderr and return code with capability checks. The test requires no successful request before the
retry boundary, exactly one complete request afterward, exact original JPEG cache size/SHA-256,
changed failure/recovery screenshots and the established account/network/filesystem isolation.

Scoped Ruff format/check and split-scope mypy pass, and the Android test collects. This worker ran
the eight real HTTP fixture cases under the outer loopback-only namespace; all passed. No APK build
or Android guest was run, so native failure, cleanup, rendering and retry remain coordinator-owned.

Coordinator source review removes an incorrectly nested remote `sh -c` invocation from cache
inventory. Size and digest are read as separate quoted toybox commands, matching the verified
original external-cache probe. Native execution remains pending.
