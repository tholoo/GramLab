# Verify original photo cancellation and out-of-order completion

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: 48 for native execution

Coordinator owns this ticket, new `tests/probes/android_media_interactions.py` and
`tests/test_android_media_interactions.py`, plus bounded monotonic timing observations in
`tests/probes/media_transfer_server.py` and its HTTP tests. Freeze the observer contract in ticket
48 before integration; worker capture framing owns the existing lifecycle probe separately.

Use three independent app/cache cases: original UI cancel/retry without restart; two visible
messages sharing a transfer with one consumer canceled; and an old transfer completing after a
live edit changes only one of its two consumers. Original input must use fresh, identity-bound
observed control rectangles after an original screenshot. No direct callback/loader substitution.
Compare exact requests, native transfer outcomes, cache bytes and per-message image bindings.
Require no stray partial files. Observe new asset success before releasing old asset and preserve
both original captures. Preserve the original 5-second client read timeout; fail missed scheduling
preconditions explicitly. Keep XML dumps and full inventories outside the critical gated window.

Also check absent activation, mismatched observation identity and stale output rejection. Maintain
all established dedicated guest, account, network and filesystem isolation checks. These tests do
not establish execution of FileLoader's duplicate branch unless its coalesced event is observed;
user-visible shared loading and the loader boundary must be reported separately.

Run focused fixture/static checks first; coordinator prepares and builds the reviewed combined
GPL source under android-build, then runs dedicated guests serially under android-gate. Retain
behavioral reds and all original evidence. Combined native regression remains required after this
batch stabilizes, followed by the remaining approved operational milestone features.

## Native red evidence

The observer APK through patch 0020 compiles offline in 2m23s. In the first original interaction
run, the observed loading control is tapped 1.3 seconds after the controlled first bytes, but no
transfer cancellation appears before the 4.8-second scheduling deadline. The trace has one start
and one coalesced load. Preserve this red and repeat with immediate post-tap state before changing
loader behavior. The same APK's real-bot lifecycle obtains a fully framed ordinary photo/caption,
but exposes a missing external JPEG copy after edit and a real new download after restart; the
cache/restart assertions correctly remain red. These are incomplete acceptance, not passed cases.
Ignored first-run evidence is `artifacts/media-interaction-native-01.xml` and its matching log,
source provenance and per-test directories. Guest/build processes for that first run are terminal.
