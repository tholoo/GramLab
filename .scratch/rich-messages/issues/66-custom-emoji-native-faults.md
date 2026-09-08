# Exercise original custom-emoji lookup failures and explicit recovery

Type: feature
Status: ready-for-agent
Work state: claimed; host harness integrated, native acceptance pending
Blocked by: shared-thumbnail failure diagnosis

Own this ticket and new `tests/probes/android_custom_emoji_faults.py`,
`tests/test_android_custom_emoji_faults.py`, `tests/probes/custom_emoji_fault_server.py`, and
`tests/test_custom_emoji_fault_server.py`. Do not change production, APK patches, existing probes,
fixtures or shared docs. Coordinate any helper dependency with ticket65; do not copy unfinished
worker implementations. Implement the test/probe only; coordinator owns all guest/build execution.

Construct authorized local World messages with registered original static/animated fixtures and
run the original application through NativeAssetProxy plus a controlled loopback HTTP peer. The
peer may fault only selected document responses or hold selected asset bytes; preserve all other
actual bridge exchanges. Retain independent HTTP tests for the fault peer before native use.

Cover three document faults: whole-request 404 for a single authorized ID, 404 for a naturally
batched pair with one lookup-unavailable ID, and a partial 200 document/dependency response for a
naturally batched pair. Do not force original scheduling: if the requested pair is not observed,
retain the failure and report batching unproven. Verify exact phase-local request/status/bytes,
original runtime request/error trace, zero asset GET on rejected lookup, stable UI and no further
lookup during a bounded idle observation window. Do not claim an unbounded absence of retries.
Retain failed-state original screenshots/XML/logcat before recovery.

Use same-process navigate-away/eviction/reopen where supported to observe a new fetch after a
failed owner; derive the wait from original eviction behavior, do not guess a sleep or change the
cache. Then force-stop, prove the dedicated PID is gone, select the healthy local bridge and COLD
relaunch unchanged content. Require a new successful document lookup and actual original rendering
with the expected bytes. Keep each World/app cache isolated. One guest may host multiple serial
subcases using explicit reset of only the dedicated synthetic app after preserving each subcase's
complete evidence; no personal state or emulator sharing with another test.

Add a separate shared-thumbnail case if it can use these owned files: two visible logical IDs with
one thumbnail asset, hold its original transfer, remove one carrier while the other remains, then
release. Require one actual asset GET and surviving original rendering with exact destination bytes.
Do not require a FileLoader coalescing trace if ImageLoader coalesces before it. Exact stale-owner
object identity and removed-receiver late-delivery assertions require separate private observation;
report those limits rather than claiming them from a passing UI or broadening instrumentation.

Follow AGENTS, TESTING, offline safety and parallel workflow. Use the assigned checkout and pinned
environment; focused real HTTP/pure checks plus scoped typing/format/lint only. No guest or build
until explicit coordinator assignment. Retain red/green JUnit/logs and return a clean frozen branch,
all processes terminal, with original native execution and internal-race gaps clearly open.

## Worker result

The owned harness stages four isolated v4 Worlds. Three exercise a single 404, a naturally
scheduled two-ID 404 and a partial 200; each retains phase-local document/asset journals, bounded
idle evidence, original trace/UI, an optional post-eviction same-process refetch observation and
an explicit force-stop/COLD healthy recovery. The fourth uses two distinct static document IDs
with the same original thumbnail, holds its one actual HTTP response, removes one carrier and
requires the surviving carrier's complete authored diamond plus exact destination bytes.

The local HTTP peer and World/geometry checks pass seven focused tests. The Android case collects
but remains unexecuted as assigned. A false `batch_observed` or `same_process_refetch` is retained
as a narrow original-behavior limit. Journals and UI do not establish callback-owner identity or
delivery into the removed receiver, and the assertions do not claim either internal property.

## Coordinator integration

Frozen tip `77cc5853262ec62b0eb9778d9b22af68c9133425` is integrated. Seven focused
HTTP/staging/diamond-oracle tests pass in 5.27 seconds, with scoped Ruff/format and strict typing
checks passing. The Android case is deselected explicitly, not reported as a pass.

The reviewed fixture uses two distinct static logical IDs sharing one thumbnail; ticket65 owns
WebM playback. Mixed/partial cases require an actual naturally batched pair, and the mixed peer
leaves ID1 available while ID2 is unavailable. Missing batching must remain a failed/unproven
case. Same-process refetch remains a bounded diagnostic, and callback owner identity and removed
receiver delivery remain separate observation gaps. The earlier disk-space cleanup requirement is satisfied. The coordinator has started the first
serial native execution on the verified immutable normal24 APK. No failure/recovery screenshots
or native report are accepted until that run completes and its assertions are reviewed.

## First native run

The first normal24 native run fails in 296.73 seconds during shared-thumbnail cache settlement,
after the three document-case functions returned. Complete per-case result objects were only
held in memory and are missing from the final empty result, so the earlier cases cannot be
counted as fully accepted. Their screenshots, traces and cache artifacts remain useful evidence.
Ticket87 adds durable completed-case checkpoints and bounded failure diagnostics before rerunning.
Cancellation is unproven: no final native media trace was retained. Original ImageLoader aggregates
receivers by URL before filtered keys; its global cancellation must not be changed on speculation.
The adapter read timeout during the deliberate partial-response hold is another hypothesis that
needs timestamps and native terminal trace evidence.

## Isolated held-transfer control

A coordinator-only local HTTP control uses the actual World, fault peer and NativeAssetProxy,
with the same 70-byte shared thumbnail and no Android client or message edit. A one-second
partial-response hold delivers all 70 bytes; a six-second hold fails after 5.003 seconds with
`IncompleteRead`, while the proxy records zero delivered bytes and `transport_error`. The peer
still records a 200 response and 70 intended bytes. Evidence is retained in the dedicated
`held-thumbnail-transport-control` artifact. This proves that the proxy's five-second timeout
can defeat the held-transfer fixture without any native cancellation. It does not establish
the first native run's actual hold duration or terminal event; the fresh checkpointed native
run remains necessary to distinguish that failure. Do not change loader ownership or timeouts
from this control alone.

## Checkpointed native rerun

The second normal24 run fails in 244.62 seconds at shared cache settlement. It durably retains all
three complete document results; replaying the unchanged original document-case assertion loop
passes all three cases and validates six original failed/recovered captures. The whole JUnit stays
failed. The shared failure record measures a 5.4607-second hold, while the proxy terminates after
5.0038 seconds with zero delivered bytes and `transport_error`, before release. The actual trace
contains media_load_start followed by media_load_failure and no media_load_cancel. Trace, cache,
logcat and peer/proxy journals survive. This confirms the transport-stall mechanism in the rerun;
ticket89 corrects the test stimulus/transparent proxy while preserving native timeouts and behavior.
Evidence: `artifacts/custom-emoji-faults-native-02.xml`, the dedicated run's failure/checkpoint
JSON, native trace and `document-checkpoint-acceptance.json`. Whole-run isolation-result acceptance
is still unavailable because the failing probe did not return its final result.
