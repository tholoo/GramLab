# Observe v4 native document and asset requests independently

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: none

Own this ticket, `tests/probes/native_asset_proxy.py` and `tests/test_native_asset_proxy.py`.
Extend the established real HTTP fixture proxy for v4 snapshot/changes/callbacks/messages/assets
and `POST /v4/custom-emoji-documents`, preserving v3 behavior and its exact existing asset-journal
shape. This is test observation, not another production transport. Do not edit production, Android
patches, shared docs, media fixtures, locks or other probes/tests.

Add `document_requests() -> list[dict[str, Any]]` returning detached records with exactly
`sequence`, `phase`, `custom_emoji_ids`, `status`, `bytes`, `started_ns`, `finished_ns`, `error`.
Sequence is one-based within this document journal. IDs preserve the request's ordered canonical
decimal-string list; phase is captured at request start; other fields match the established asset
journal meanings. Both methods return snapshots under the same lock, including detached ID lists.
No capability, URL, response body or per-ID existence result enters the journal. Asset `requests()`
continues to contain only asset GETs, with no new required fields or changed counters.

Document lookup accepts only the frozen v4 JSON request (1–200 canonical positive signed-64-bit
strings, exact `custom_emoji_ids` member and at most 16,384 bytes); malformed requests reject before
forwarding. Preserve valid whole-batch 404 responses from upstream with no invented success.
Authenticate and enforce bounded single Content-Length/no Transfer-Encoding, exact local routes,
and selected loopback destination. Do not follow redirects. Retarget/phase changes must not relabel
in-flight requests. Unknown/wrong-version/external/Bot API paths remain rejected.

Use independent actual local HTTP peers to test response preservation, complete/missing/interrupted
documents, wrong capability, malformed/repeated JSON and framing, phase transitions, retargeting,
copy isolation and absence of sensitive request material. Run existing 12 asset proxy tests too.
Write behavioral red first. Retain unique JUnit/log output in ignored artifacts; do not delete it
before coordinator review. Use this worktree's tools/dev and outer loopback-only namespace; verify
imports and tools/worktree check before edits/resume. Run scoped Ruff/format and strict mypy using
the existing explicit-package-bases convention. No Android build/guest/full core gate. Commit owned
files and send a frozen clean tip/base, exact checks, retained evidence and terminal process state.

## Answer

Implemented on `task/custom-emoji-request-observer` from base
`42430827b170df7bf66bfc22dd51fdc616dcaffc`. The proxy now forwards the exact v4 bridge route set,
validates bounded custom-emoji document requests before forwarding, and records those requests in
a lock-protected journal separate from asset GET observations. Actual loopback HTTP peers cover
response bodies and headers, whole-batch 404, interruption, redirects, authorization and framing,
phase/retarget identity, detached snapshots and rejected nonlocal or wrong-version paths.

The guarded behavioral red is retained as
`artifacts/custom-emoji-request-observer-red.{log,xml}` (16 expected failures). The final guarded
suite is retained as `artifacts/custom-emoji-request-observer-green-final.{log,xml}` and passes all
31 cases, including the 12 pre-existing cases. Scoped Ruff lint and format plus strict mypy pass;
their logs are retained under `artifacts/custom-emoji-request-observer-{ruff,format,mypy}.log`.
Coordinator integration and combined verification remain pending, so the work state stays claimed.
