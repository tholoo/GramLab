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


## Normal21 observations and remaining acceptance

The same first-photo cancel/retry case reaches cancellation 1.21 seconds after initial bytes,
then an explicit original download tap completes the exact PNG with no stray partial file.
Retained host assertions pass for its request counts, receiver bindings, cache bytes and all
three activation guards; the original combined JUnit stays failed for the other two cases.
All 41 original files are unchanged. Visual inspection confirms canceled/download and completed
photo states, but finds the loading capture predates visible message cells. The probe now waits
for original drawn cells, captures, then obtains a fresh input sample. Its new capture order
requires a native rerun; the retained report is not complete visual acceptance.

Shared loading continues after canceling one receiver: the second displays the photo, but the
canceled first receiver loses its download icon after completion without displaying the image.
Do not tap a nonexistent download control or alter the original renderer to satisfy that oracle.
The ordinary live edit cancels the old shared transfer through original MessagesStorage cleanup;
this is not proof of old transfer completion after edit. Source inspection suggests a richer
fixture with an unchanged leading rich photo and a replaced second photo can retain the old
transfer; this remains a native hypothesis requiring exact receiver observation.

Ignored evidence: original `artifacts/media-interaction-native-03.xml`, retained case assertion
receipt `artifacts/media-cancel-retry-retained-02.json` and matching `retained-04.log`. Local run
wrappers accidentally reused the first input-manifest name; its surviving contents are verified
as run03 and copied to a distinct name. Earlier APK/staged-source fingerprints remain verifiable,
but their overwritten pre-run manifests are unavailable. The explicit recovery receipt preserves
this limitation; do not infer full earlier host/profile equivalence. Historical wrappers now
refuse reuse before writing anything.


Independent original-source review resolves the shared-cancel oracle: ChatMessageCell's ordinary
cancel removes the first ImageReceiver from ImageLoader's CacheImage; the remaining receiver
keeps its HTTP load alive. Bitmap completion iterates only remaining receivers, while the separate
fileLoaded notification reaches the canceled cell, sets progress to one and selects ICON_NONE
because the file now exists. There is no original post-completion download button. The corrected
case therefore asserts one request, coalescing, only the second bitmap, both controls absent and
exact cache bytes. It retains cancel/retry as a separate original first-photo interaction.
Source anchors in the pinned tree: ChatMessageCell didPressButton/onSuccessDownload/updateButtonState,
ImageReceiver cancelLoadImage and ImageLoader CacheImage removeImageReceiver/setImageAndClear.
This corrects the test oracle to original behavior; no renderer or loading implementation changed.
A fresh native run must verify the updated case and its three framed captures.


Fresh normal21 run04 confirms both corrected cancel/retry and shared-consumer assertions,
including all activation guards. All six primary PNGs are inspected: loading controls are visible
before input, canceled cells show the expected download control, retry displays exact image, and
shared completion displays only the remaining receiver's image. The sole combined failure is
still ordinary late-edit cleanup. `artifacts/media-interaction-native-04/` keeps unique inputs,
JUnit, log, both per-case HTML reports and completion receipt: zero changed sources, four exact
staged probe fingerprints and unchanged APK. No former failed JUnit or screenshot was replaced.

## Ordinary-edit cleanup acceptance

The coordinator is correcting the ordinary `late-edit` case to the original global-cleanup
contract; the stronger old-transfer completion requirement remains assigned to ticket 55.
Retained run04 records one successful new JPEG and one canceled old PNG, one coalesced old load,
and repeated original receiver states: the edited cell displays the JPEG without a control;
the unchanged shared cell has no bitmap and retains its cancel/progress control. The original
failure expected both images and remains preserved. No renderer/loader behavior is changed.

Fresh acceptance must observe native cancellation before releasing the old HTTP response, await
that response's termination, and verify two fresh unchanged receiver samples, the exact new JPEG
cache and no old/partial bytes. Server termination does not count as native success. The test
continues to require real cancel/retry and shared-consumer input plus schema-1 activation guards.
Native verification on the combined normal23 build remains pending.
