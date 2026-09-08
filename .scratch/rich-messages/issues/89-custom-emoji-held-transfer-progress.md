# Preserve an active shared transfer through native observation

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: coordinator integration and native execution

Own this ticket, `tests/probes/custom_emoji_fault_server.py`,
`tests/test_custom_emoji_fault_server.py`, `tests/probes/native_asset_proxy.py`, its focused tests
`tests/test_native_asset_proxy.py`, and the shared-case scheduling in
`tests/probes/android_custom_emoji_faults.py`. Coordinate any additional file ownership with root.
No production, APK, profile, default network timeout, asset bytes, renderer or shared-doc changes.

The second native66 run reproduces failure in 244.62 seconds. The intentional response hold spans
5.4607 seconds. NativeAssetProxy records zero delivered bytes and transport_error at 5.0038 seconds,
before release; the actual native trace records media_load_start then media_load_failure, with no
media_load_cancel. All three completed document checkpoints pass their original acceptance loop.
A real World/peer/proxy HTTP control already reproduces the transport failure without Android/edit:
one-second hold delivers all 70 bytes; six-second hold fails at five seconds. Preserve these reds.

The shared-consumer case needs an unfinished transfer while one carrier is removed, not a transport
stall exceeding the client's read timeout. Correct only this test stimulus and observation plumbing.
NativeAssetProxy currently buffers `read(65536)` and does not forward a short partial response until
completion. Make the observer transparently forward available bytes, preserving exact bytes/status/
headers, request journals, truncation/error accounting and local endpoint restrictions. Add a bounded
opt-in progressive hold for this shared case: send original response bytes slowly enough to keep the
transfer unfinished until explicit release while making progress within the unchanged read timeout.
Reserve final bytes for explicit release; never synthesize padding, report a premature completion,
loop indefinitely or change existing default stall fault behavior. Explicitly reject an unsupported
progressive schedule/body size rather than silently bypassing the intended observation. Keep reset,
case order, original edit and all successful result/acceptance shapes unchanged. Completed/checkpoint
and failure-only diagnostic behavior from87 must remain intact.

First establish real HTTP controls for the observer's missing early-byte forwarding and for the
end-to-end progressive hold crossing the unchanged five-second boundary: client sees exact prefix
before release, no complete result before release, original full bytes exactly once after release,
and accurate request/error journals. Preserve an actual stalled timeout/truncation rejection control.
Do not use sleeps to infer native edit application; existing actual UI observation remains required.
Run focused isolated HTTP/staging tests and scoped lint/format/strict typing only, no guest/build/full
gate. Worker owns implementation and handoff; root owns fresh native66 rerun and combined checks.
A host HTTP pass alone does not establish native shared-receiver acceptance.
