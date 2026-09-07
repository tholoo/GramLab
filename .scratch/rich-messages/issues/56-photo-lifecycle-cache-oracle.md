# Verify photo lifecycle against original destination cleanup

Type: bug
Status: ready-for-agent
Work state: claimed by photo-lifecycle-cache worker
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

## Worker handoff

Owned changes are this ticket, `tests/probes/android_media.py`, `tests/test_android_media.py`,
and the authorized bounded helper `tests/probes/native_asset_proxy.py` with
`tests/test_native_asset_proxy.py`. No shared fixture/server/helper, native source, patch, APK,
profile, rendering, transport guard or timeout was changed.

The real-bot probe now starts its edited phase before returning the initial observation to the
bot scenario. Restart gets a distinct boundary after force-stop. Each phase requires its own
initialization/edit event, exact new loader start/success totals and independently observed native
GET totals, successful complete HTTP bodies, exact selected destination paths/digests/sizes and
empty internal/external `*.gramlab-*.part` scans. Hashing follows transfer completion. The final
ordered trace is partitioned without gaps; late work cannot borrow a previous phase's success.
The four original captures, seven-gesture complete ordinary framing bound, full semantic
round-trip assertions, cold launches, accounts and runtime isolation checks remain required.

The exact transfer counts by asset 1/2 are initial 1/2, edit 1/0, restart 0/1. PNG starts only in
the image directory, then exists in both directories. JPEG starts in both, loses only its image
copy after edit, and regains that copy through a new restart GET. JPEG messages are rich messages;
its image-directory copy does not imply an ordinary JPEG message. Original MessageObject.getPhoto
selects the first rich photo; MessagesStorage's changed-photo cleanup selects the non-force-cache
path. RichMessageLayout uses cache type 1 and ChatMessageCell.fileAttach may select type 0.
Original FileLoader/FileLoadOperation also validate the selected destination. These observations
justify the bounded oracle, not suppressing original deletion or claiming universal cache reuse.

The test-only proxy forwards only the configured authenticated loopback bridge and bounded
known fixture routes; it does not follow redirects. Scenario-owned asset reads keep using the
actual bridge directly. Only native asset GETs enter its sanitized sequence/phase/asset/status/
byte/timing/error journal. Reopening the bridge retargets the proxy while preserving its native
endpoint and exact World/persona/capability binding. HTTP handler sockets have bounded waits;
shutdown waits for owned handler/server threads. It requires the isolated loopback namespace.

A second native test creates one ordinary PNG through public World operations. Its complete
independent v3 envelope includes now=1700000000, message_position=1, cursor/revision=4 and the
exact photo/identity descriptors. After COLD restart it requires the same image-directory bytes,
zero new loader starts/successes/asset GETs, and a fresh exact-identity original photo observer
result showing the current ImageReceiver has the full image. Both photo/caption captures must be
fully framed. The control produces two report captures and makes no claim about edited rich
photos. The full snapshot oracle is also exercised through actual guarded ClientBridge HTTP.

Verification from the checkout-local pinned environment:

- `tools/worktree check photo-lifecycle-cache`; `tools/dev default --command uv sync --locked`;
  imported gramlab resolves to this worker checkout.
- `tools/dev default --command unshare --user --map-root-user --net bash -eu -c
  'ip link set lo up; .venv/bin/pytest tests/test_native_asset_proxy.py
  --junitxml=artifacts/ticket56-proxy.xml'`: 12 passed, 3.35 seconds. Covers exact body/status and
  redirect preservation, wrong auth/route/target rejection, actual closed/reopened ClientBridge
  retarget, missing asset, complete control snapshot and exclusion of direct scenario GETs.
- Scoped Ruff lint/format and `git diff --check` pass.
- `tools/dev default --command uv run --locked mypy tests/probes/android_media.py
  tests/test_android_media.py` passes. Separate
  `tools/dev default --command env MYPYPATH=tests uv run --locked mypy --explicit-package-bases
  tests/probes/native_asset_proxy.py tests/test_native_asset_proxy.py` passes. Separate scopes
  preserve the staged standalone-probe and imported test-module layouts.
- `tools/dev default --command uv run --locked pytest tests/test_android_media.py --collect-only`:
  two native cases collected; no worker guest or APK build was run.
- Worker-local ignored `artifacts/ticket56-retained/check.py` replays the untouched normal20
  `media-interaction-native-01/test_real_photos_render_edit_c0` result. The baseline oracle fails
  its initial-path-subset assertion. Corrected exact cache and phase transfer totals pass, and
  wrong bytes, missing rich JPEG cache and undeleted JPEG image-path mutations all reject. The
  preserved full semantic/framing/cache/media-shape checks reach the new mandatory phase evidence
  requirement and reject the old artifact's absence of it. Results are retained in
  `artifacts/ticket56-retained/result.log`; no old artifact/report was rewritten.

Remaining acceptance belongs to the coordinator: fresh serial original-APK real-bot lifecycle
and unchanged-photo control under android-gate, plus screenshot/report inspection. Old evidence
cannot prove the new native-only GET counts, phase boundaries, no-parts gate or unchanged control.
Exact scheduling/directory disagreement must fail visibly and be diagnosed, not force a schedule
or relax bytes, framing, semantics, no-DC or isolation requirements. Keep this ticket claimed until
both fresh native cases pass. Shared handoff/compatibility/contributor check documentation remains
coordinator-owned. No worker server, bot, build or guest process remains active at handoff.

## Coordinator native checkpoint

The integrated normal23 run passes the real-bot lifecycle in 81.52 seconds: exact phase-local
native requests, original destination cleanup/reload, bytes, no parts, semantic comparisons and
cold restart all pass. All four original captures are inspected, including the fully framed
ordinary photo/caption. The combined JUnit stays failed because the new unchanged control's
framing helper rejects its non-scrollable RecyclerView despite the original photo/caption fitting
on screen. Retained `initial-framing-0.png` and XML prove that condition; no native loader defect
is inferred from a host hierarchy assumption.

The helper now selects the caption's actual containing RecyclerView without requiring scrolling.
Untouched native XML first reproduces the old rejection, then yields the independently specified
frame [0,231,320,532] inside viewport [0,80,320,532]. A decoy unrelated scrollable list is rejected.
Scoped Ruff/strict mypy pass. Native verification of the corrected helper and unchanged COLD
restart remains required. Evidence: `artifacts/media-lifecycle-and-rich-late-native-03/` preserves
all three original cases, failed JUnit, unchanged APK/source receipt and 16 staged probe checks;
`artifacts/unchanged-photo-framing-retained-01.log` retains the exact geometry/rejection check.
