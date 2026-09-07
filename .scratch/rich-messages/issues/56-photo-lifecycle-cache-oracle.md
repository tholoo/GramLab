# Verify photo lifecycle against original destination cleanup

Type: bug
Status: ready-for-agent
Work state: open
Blocked by: none for host/probe corrections; coordinator owns native execution

Own this ticket, existing `tests/probes/android_media.py`, `tests/test_android_media.py`, and
if needed a new bounded test-only native asset request proxy and its focused HTTP tests.
Coordinator owns shared media fixtures/server, native patches/build/guests and shared docs.
Request ownership expansion before changing the real-bot semantic fixture or broad test modules.

Retained normal20 framing run is a behavioral red: the host requires every initial file path to
survive edit and every edited path to survive restart with no new transfer. Original source and
retained caches contradict this. There is no ordinary JPEG message in this fixture: asset 2 is
in rich messages. Original ChatMessageCell fileAttach can request its MEDIA_DIR_IMAGE copy while
RichMessageLayout requests the cache directory. Replacing the first photo in a rich message
selects that old photo through MessageObject.getPhoto; MessagesStorage deletes its image-directory
path. Original FileLoader/FileLoadOperation also check their selected destination. A later
request can reload that path despite an intact independent cache copy. No adapter defect is
established by destination-specific lookup alone; do not modify original cleanup or rendering.

Preserve and independently verify this exact existing fixture's observed cache sequence:
initial PNG in image directory, JPEG in image and cache directories; after edit PNG in both and
JPEG only in cache; restart both assets in both directories. Every copy must have exact original
bytes and no partial file. Initial successful transfers are PNG once/JPEG twice; editing adds
one PNG transfer; restart adds one JPEG transfer. These retained observations are not an excuse
to force scheduling; make each phase's prerequisites explicit and report actual disagreement.
Do not infer ordinary JPEG content from the storage directory name.

Correct the probe's lifetime-success wait: retain phase boundaries and wait for actual new phase
work and exact expected receiver/cache state before recording success. Preserve fully framed
ordinary-photo/caption captures and original rich images, complete semantic/native comparisons,
COLD restart, fresh profile/APK/source and all offline/account/filesystem checks.

Independently count native asset HTTP requests, separating scenario-owned reads. A test-only
proxy may forward only to the existing selected loopback ClientBridge and retain sanitized
asset IDs/status/timing; it must not log capabilities, widen runtime egress, follow redirects or
become a production endpoint. Verify any new helper with real guarded HTTP tests. Pair request
counts with native trace and cache bytes; server receipt alone is not native success.

Add an unchanged-photo restart control proving the selected valid destination survives, the
original image renders and no new native asset GET occurs. This is bounded cache reuse evidence;
retain the separate original-edit cleanup/reload behavior rather than claiming universal reuse.
Keep captures/reports bounded and preserve all original failed artifacts. No user profile,
renderer, timeout, density or viewport changes to make the test pass.

Use existing retained red evidence plus independently specified corrected host assertions and
focused static/HTTP checks before handoff. Coordinator runs fresh serial native acceptance and
inspects images/reports under android-gate. No worker APK/guest. Send frozen clean commit, exact
source/retained evidence supporting the oracle, helper scope, commands and remaining native risks.
Keep claimed until full integration acceptance, including the unchanged-photo control, passes.
