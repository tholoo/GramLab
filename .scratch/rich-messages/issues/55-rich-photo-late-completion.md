# Prove late completion through an edited original rich photo

Type: feature
Status: ready-for-agent
Work state: resolved
Blocked by: 53 for native execution only

Own this ticket and new `tests/probes/android_rich_media_late.py` and
`tests/test_android_rich_media_late.py`. Coordinator owns existing media probes/server helpers,
shared docs, source/patches, APK and all guest runs. Reuse the controlled HTTP MediaTransferServer
and original Observation's bounded identity/age/window logic where suitable. Request bounded
helper changes from the coordinator instead of duplicating or silently widening ownership.

Consume the private schema-2 observer contract in ticket 53: ordered targets with message_id,
kind and bounded asset_ids; result reports actual asset_id and kind, original receiver geometry,
key and has_image. Rich icon/progress are null. Preserve strict nonce/World/persona/peer/PID,
fresh generation/age and finite visible bounds before accepting evidence or performing input.
No reflection, loader calls or public target API. This case needs live editing but no photo tap.

Use two messages and three distinct original photo assets: a rich message with direct root photo
A first and B second; an ordinary message also using B. A can be the existing square PNG, B the
4:1 landscape PNG (`photo-landscape-48x12.png`) and C the existing JPEG. A is complete locally; B is held after first bytes on one
controlled HTTP request. Target the rich message allowing B/C and the ordinary message allowing
B, so unchanged leading A cannot be mistaken for the target. Both target images must be visibly
observable; use bounded original framing if necessary. Capture only after drawn cells are ready.

Publish a full v3 live edit replacing only rich B with C, keeping leading A byte/ID-identical.
Prove C succeeds and the original rich receiver binds C before releasing B's already-started
response inside the unchanged 5-second client read timeout (4.8-second orchestration deadline).
After release, require one B request total, observed native coalescing, exact B cache bytes and
successful original ordinary receiver display. Require edited rich target to remain C across
fresh post-release samples, with no B rebound and no stray partial file. Native success is required;
server write completion alone is insufficient. Preserve exact snapshot/change/revision, HTTP
requests, native trace, all app-owned matching cache copies, receiver samples and primary captures.

The source premise is pinned MessageObject.findPhoto returning unchanged first photo A, so original
MessagesStorage skips whole-message old-photo cleanup. Do not disable that cleanup. Keep existing
ordinary-photo edit/global cancellation evidence in ticket 49 and state this scenario's precise
scope. It proves an old transfer can complete after replacing one of its consumers; it is not a
claim that ordinary edits never cancel old media or that observation sees every render frame.

Add native schema-2 activation guard fixtures for malformed target/type/ID/list values, duplicates,
wrong asset/ambiguous target and missing/unavailable original view, preserving existing absent/
World/process guards. Prefer one dedicated guest with bounded independent app resets. Failed
cases must retain evidence without preventing independent later guard cases; do not hide failure.
The report must be self-contained with at most four primary original captures and isolation/
profile metadata. Whole failure remains failed if any required interaction or guard fails.

Run scoped Ruff/format/mypy, independently construct fixtures and collect tests using the assigned
checkout's pinned environment. No worker APK/guest. Coordinator builds normal observer APK, runs
native acceptance under android-gate, reviews images and retains behavioral red/green evidence.
Send frozen clean commit, helper dependency requests, exact expected outputs and remaining runtime
assumptions; keep claimed until integrated native acceptance. Preserve original renderer/fidelity.


Coordinator fixture dependency: the shared HTTP server now preserves snapshot identity
records in an empty initial v3 change response. Strict native mention-enabled clients require
those base identities even without message changes. A real HTTP regression first fails on the
empty list and then verifies the corrected complete envelope. This is test-server fidelity, not
a World/bridge schema change. The original 4:1 PNG uses the established deterministic generator;
all earlier PNG bytes remain unchanged.

## Worker implementation

The dedicated probe independently constructs the initial and edited snapshots. It gates exactly
one B response after its first bytes, observes rich B and ordinary B through the schema-2 identity
set, publishes the complete B-to-C rich edit, and requires an original C binding before releasing
B within 4.8 seconds. Four primary captures cover loading, C binding, B completion and a later
stable sample. The host oracle checks the exact edit journal, one B request, native coalescing,
successful C/B terminals, every matching final cache copy, no partial file and no B rebound in
every retained post-release sample. A remains the byte-identical leading rich photo.

Eighteen reset-isolated schema-2 guards cover malformed envelope, target and identifier values,
duplicates, wrong asset, ambiguous rich roots, missing message and wrong target kind. Malformed
activations must publish no result; valid unavailable targets must publish their exact reason.
Failure in any guard fails the whole probe while preserving completed earlier evidence.

Scoped Ruff formatting/checking, mypy and pytest collection pass in the checkout's isolated pinned
environment. No APK build or Android guest was run. Native acceptance remains coordinator-owned.
The new 4:1 B is expected to render about 60--67 pixels high at the bounded 320-pixel viewport,
which leaves room for the original 48dp control at 160 dpi; native geometry remains to be proven.

The rejection follow-up waits for an explicit native `startup_rejected` event instead of treating
an observation file that has not appeared yet as rejection. Malformed cases retain their complete
raw trace and must contain no `initialized` event or asset request. Lookup failures verify their
full schema, nonce, World, persona and peer identity as well as the exact unavailable reason. A
live-case failure now retains partial trace, requests and best-effort cache evidence, releases the
gated response, stops the app and continues through the complete independent guard matrix. Host
acceptance rejects any live, evidence or guard failure after the probe preserves those results.

Follow-up review removed the unrelated A/B request-order assumption while retaining exact
per-asset fault counts, B's partial-response deadline and C-before-release native ordering. Every
guard now records its own failure and reaches the independent force-stop/reset before the host
oracle rejects the complete matrix. Source-aligned unavailable reasons are `unsupported_photo`
for a rich allowed set with no matching root and `asset_mismatch` when a rich message is requested
as ordinary. Loading and final samples also require the exact B receiver key. The main observation
poll performs one result read per iteration; there is no repeated consecutive read around the
loading capture. Focused Ruff, mypy and collection checks pass after these corrections.

## First native checkpoint

Normal23 reaches the complete live interaction: original rich C binds before B is released,
then ordinary B loads while rich C remains bound in fresh observations. All four original PNGs
are inspected. The combined run remains failed: the host expected a sized rich image key, and
one of 18 guards times out waiting for activity launch before reading its rejection trace.
The original rich full-image call supplies a null filter (RichMessageLayout applyImage); the
ImageReceiver appends `@filter` only for a non-null filter. Rich keys therefore equal `2_1` and
`3_1`; ordinary B retains its independent sized key. The corrected host oracle preserves both.
Guard intent dispatch now proceeds directly to the existing bounded native trace/result wait;
rejected startup need not produce a drawn activity. No client timeout or renderer is changed.

Retained `artifacts/rich-and-ordinary-photo-interactions-01/` contains the original failed JUnit,
147.14-second rich case, all 18 independently attempted guard results, screenshots and unchanged
source/APK receipt. The same run passes the separate ordinary interactions in 99.43 seconds.
Fresh rich guard and complete host acceptance remain required; do not relabel this JUnit green.

The second native run passes all 18 guards and again reaches the complete four-capture B/C
interaction. It exposes a separate fixture error: leading A can have one coalesced request or
one request per original image/cache destination. The fixture supplied only one complete A body;
a legitimate second request received its default missing fault. Original MessageObject.findPhoto
selects leading A for ChatMessageCell.fileAttach (cache type 0), while RichPhotoBlock uses type 1.
FileLoader coalesces concurrent final filenames, but later requests check their chosen destination.
Independent source review confirms the one-or-two request boundary; no A-before-B order is promised.

The fixture now offers two complete A responses and requires matching one-or-two native A
starts/successes, only allowed original destinations with exact bytes, and no failure/cancel or
partial files. B and C still require exactly one request/success each and all pre-release and
post-release receiver invariants. `artifacts/rich-photo-late-native-02/` preserves the unmodified
failed run, complete guard results, captures and source/APK receipt. Fresh full acceptance remains
pending; this corrects auxiliary fixture availability without changing original media behavior.

## Answer

The complete normal23 case passes in 105.85 seconds with the held response released after
3.29 seconds, inside the unchanged read deadline. A uses both allowed original destinations;
B and C each have one successful request. Exact native transfer/cache/receiver assertions and all
18 guard cases pass. Four original captures and desktop/mobile HTML report are inspected, with
all images embedded, no horizontal overflow and no external subresource requests.

Evidence is `artifacts/media-lifecycle-and-rich-late-native-03/`, whose complete receipt verifies
unchanged APK/source and 16 staged probe fingerprints. Its combined JUnit remains failed solely
for the independent unchanged-photo framing case subsequently corrected in ticket 56. The rich
case's own JUnit entry and generated report pass; no failed historical result is rewritten.
