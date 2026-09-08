# Preserve an active shared transfer through native observation

Type: bug
Status: ready-for-agent
Work state: implemented on `task/custom-emoji-held-transfer-progress`; coordinator review pending
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

## Implemented boundary and focused evidence

`NativeAssetProxy` now consumes `HTTPResponse.read1()` and flushes each available chunk to the
native client. It retains the original status and selected headers, increments journal bytes only
after a successful downstream write, and marks any fixed-length response that reaches EOF early as
`transport_error` for both document and asset requests. Exact partial bytes remain visible to the
client, whose preserved `Content-Length` rejects the truncated response.

The existing fault peer's default hold remains a fixed stall. Its opt-in progressive mode validates
a 0.05–4 second interval, a bounded final-byte reservation, and enough original body bytes to make
progress for the complete existing 30-second hold bound. Invalid schedules, empty bodies and bodies
too short for that schedule fail explicitly. An admitted hold sends the original first half, then
one original byte per interval, and keeps all remaining bytes including the reserved final byte
behind explicit release. Timeout closes an incomplete response; release sends every remaining
original byte exactly once. The shared native case alone selects a one-second progressive interval;
its case order, UI/edit schedule, defaults, timeouts and successful result shape are unchanged.

The retained real-HTTP red `artifacts/custom-emoji-held-transfer-red.xml` shows the former proxy
withholding an upstream-flushed prefix until timeout, failing to journal a short asset body, and
lacking the progressive API. The final isolated suite in
`artifacts/custom-emoji-held-transfer-final.xml` passes all 43 proxy/peer checks. New controls prove
early prefix visibility, exact complete bytes, fixed-length truncation, an unfinished progressive
transfer across five seconds, explicit release, unchanged default five-second stall failure and
invalid schedule/body rejection. Scoped Ruff, format and strict mypy pass. No guest, APK build or
full gate ran; original Android shared-receiver acceptance remains coordinator-owned.

## Coordinator integration

The reviewed frozen worker tip is integrated. Forty-five affected HTTP/checkpoint/staging checks
pass in 38.71 seconds, with the native case explicitly deselected. Scoped lint/format and strict
typing pass. The coordinator removed an unnecessary exact-one-progress-byte timing assumption;
a delayed scheduler may legitimately emit more than one byte. The focused control still requires
forwarded progress across five seconds, an incomplete response before explicit release and the
exact complete body afterward, and passes independently in 6.17 seconds. Evidence:
`artifacts/custom-emoji-held-transfer-integrated-01.xml` and
`artifacts/custom-emoji-held-transfer-progress-integrated-02.xml`. Fresh native03 remains required.
