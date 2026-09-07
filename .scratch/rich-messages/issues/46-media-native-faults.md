# Verify original photo download failures and recovery

Type: feature
Status: ready-for-agent
Work state: open
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
