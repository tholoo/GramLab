# Android patch queue

Base: Telegram Android `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`, with the submodules in
[`upstream-lock.json`](../upstream-lock.json). Apply in `series` order to a dedicated exported
checkout using [`prepare.py`](../prepare.py). The original checkout remains unchanged.

These adaptations contain GPL client context and are maintained under GPL-2.0-or-later, preserving
the upstream source headers. [`COPYING`](COPYING) contains the upstream GPLv2 license text.
Original preparation tooling and notes retain the root MIT license. This does not relicense the
client's separately licensed dependencies or establish distribution readiness.

`0001-build-preparation.patch` selects only the shared client library, its existing JLatexMath
dependency and a distinct `org.gramlab.android` application module. It pins the Gradle distribution
checksum, uses Google's official Maven distribution CDN, and removes cloud/distribution build
plugins from the selected build. The application uses a fresh project-local signing key and
original GramLab icon/label; the shared renderer and native sources remain unchanged at this step.
The library and APK target x86_64, with bounded native compiler/linker pools. Re-export the pinned
base and reapply the entire queue for updates; do not edit the acquired upstream checkout.

`0002-native-transport-guard.patch` enables `GRAMLAB_OFFLINE` for the JNI and tgnet libraries.
JNI request/init entry points reject before transport work; native init/socket entry points have
abort backstops. A dedicated `app_process` probe checks JNI rejection and preserved buffer operations
without installing the application. See the [native guard record](../../../docs/development/android-native-guard.md).

`0003-semantic-client-bridge.patch` adds authenticated local snapshot transport and TL user,
dialog and history conversion, plus a guest probe using the pinned serializer. See the
[semantic adapter record](../../../docs/development/android-semantic-bridge.md). It does not yet
replace application request dispatch or activate synthetic lifecycle startup by itself.

`0004-synthetic-application-startup.patch` binds the synthetic world/persona before startup,
replaces Java read request dispatch and disables cloud startup/transport paths. Its restricted
manifest enables the existing launch activity in a dedicated contained guest. See the
[application evidence and limits](../../../docs/development/android-application.md).
The real plain-text conversation renders at this step. Never install or run this build outside
the required containment.

`0005-inline-callbacks-and-live-edits.patch` translates inline callback keyboards and edit dates,
routes actual callback requests through authenticated HTTP and applies ordered semantic message
events through the existing controller. See the [callback/edit evidence](../../../docs/development/android-callbacks.md)
for the software graphics profile, real tap, interrupted bot recovery, visible edit and client
restart, along with the narrower recovery and unsupported-operation limits.

`0006-formatting-entities.patch` translates nine explicit non-link formatting types, validates
UTF-16 ranges and exposes the pinned serializer's entity output in the existing bridge probe.
Snapshot/history and live edits share the same conversion. See the
[formatting evidence](../../../docs/development/formatted-text.md) for actual text-only formatting
edits and restart observations. The patch changes only the adapter and probe; upstream message
cells, fonts and resources remain unchanged.

`0007-reconcile-cached-history.patch` refreshes all snapshot messages through upstream history
storage before opening a chat. See the [older-message recovery record](../../../docs/development/android-history-recovery.md)
for bot edits made during client downtime, subsequent messages and repeated cold restarts. The
patch retains the client database and changes only the adapter runtime class.

Preparation exports only pinned tracked files, removes upstream signing/service templates and
replaces the upstream API/hash/key fields with inert values. Their original values are not copied
into this patch queue. No personal configuration from ignored upstream files is exported.
No network request is made by preparation itself; dependency provisioning is a separate step.
Preparation also installs the committed dependency checksum record for strict Gradle verification.

Current verification and remaining compilation/runtime gates are in the
[build record](../../../docs/development/android-build.md). Continue to audit initialization,
native transport, media, WebViews, push and background networking together before activation.

`0009-native-controller-timer.patch` restores the original periodic `ConnectionsManager.onUpdate`
callback omitted when native transport was disabled. It runs on the client's stage queue,
independently of blocking HTTP polling, so the original controller can detect queued pts gaps.
See the [live-gap regression and verification status](../../../docs/development/live-gap-recovery.md).

`0010-bridge-failure-classification.patch` retains the exception class when request dispatch maps
an unexpected failure to 503. It correlates that class with the existing request token and never
records exception messages, response bodies or capabilities. This enables diagnosis of the
observed composer failure; it does not itself fix or retry a failed request.

`0011-rich-message-projection.patch` creates native `TL_iv.RichMessage` blocks and recursive text
from the semantic world representation. The shared message decoder covers snapshots, live edits
and difference recovery. A separate probe observes the full structure after native serialization;
original message cells, rich layout and resources remain unchanged. See the
[projection contract and verification limits](../../../docs/development/android-rich-projection.md).

`0012-rich-list-projection.patch` extends the semantic adapter and serializer probe with original
ordered/unordered block-item constructors, canonical labels and checkbox state. Empty item block
arrays remain empty. Strict native validation rejects inconsistent fields and optional flags.
The twelve-patch export preserves all 6,666 original UI/resource files and RichMessageLayout;
the integrated incremental offline build passes. See the [list contract](../../../docs/development/rich-list-references.md)
and [integration ticket](../../../.scratch/rich-messages/issues/09-list-integration.md) for the
separate runtime and original-rendering acceptance status.


`0013-rich-button-projection.patch` adds canonical callback/copy/disabled rows and inline buttons
to the GPL adapter and serializer observer. Labels remain recursive plain text; action/style and
alignment flags use original native constructors. Fresh preparation preserves 10,759 original
UI/resource/asset files in the broader worker comparison. The normal APK rebuild and focused native
codec and real-bot rendering/live RTL edit/restart checks pass. Combined regression and actual
rich-button input remain separate acceptance steps; see the
[button contract](../../../docs/development/rich-buttons-contract.md). The optional geometry
experiment is not part of this series or the normal APK.

`0014-quoted-code-entities.patch` corrects quote containment of code/pre in the existing
nine-entity validator. Equal extents order the quote first; all ancestors are checked to keep
emphasis/code nesting, crossing ranges and nested quotes invalid. Only `GramLabBridge` changes.
Fresh preparation and comparison of 43,268 exported files find that one adapter difference;
all 6,666 checked upstream UI/resource files remain unchanged. Integrated compilation and
runtime acceptance are tracked in [the quoted-code correction](../../../docs/development/quoted-code-formatting.md).

`0015-rich-link-text.patch` projects recursive URL/email/phone text into original `TL_iv` types
and observes the same fields after serialization. URL cached-page identity stays zero and the
independent probe checks that invariant. Only `GramLabRichMessage` and `BridgeProbe` change;
the 43,268-file comparison against normal14 finds exactly those two adapter differences, and
the patch applies without fuzz or offset. Build and actual rendering/edit/restart acceptance are
tracked in [the structured link contract](../../../docs/development/rich-links-contract.md).

`0016-rich-link-required-fields.patch` checks that each URL/email/phone node contains its visible
text and metadata before reading them. It uses the existing classified rich-message rejection,
following the normal15 missing-field failure. Only the three adapter branches change; no renderer
or exception-envelope change is included. See [the regression](../../../.scratch/rich-messages/issues/32-rich-link-required-fields.md).


`0017-local-photo-delivery.patch` maps v3 immutable local photos into original native photo
locations and delivers validated bytes through the original FileLoader/ImageLoader boundary.
`0018-persistent-photo-locations.patch` preserves these locations through an existing upstream
PhotoSize serialization constructor. `0019-required-media-fields.patch` classifies missing
required descriptors before JSON getters can escape the bridge rejection envelope. Codec,
real-bot rendering/edit/restart and response-fault evidence is recorded in the
[photo profile](../../../docs/development/photos.md); this is partial media acceptance.

`0020-photo-view-observation.patch` adds opt-in app-private diagnostics of visible original
ordinary-photo cells, controls and image receiver bindings. Activation is bound to the loaded
World/persona/peer and message IDs. The adapter reads public original getters after draw and
publishes bounded atomic observations outside the UI thread. No original renderer or input
handler changes. Missing activation installs nothing; invalid activation rejects startup.
This is a private test observation seam, not the approved public rich-target API or an atomic
input guarantee. See [ticket 48](../../../.scratch/rich-messages/issues/48-media-view-observer.md)
and [interaction acceptance](../../../.scratch/rich-messages/issues/49-media-native-interactions.md).
Compilation and focused ordinary-photo/activation checks pass; shared and late-completion
acceptance is tracked in the interaction ticket.


`0021-cancellable-first-photo.patch` reserves nonzero ImageLoader tags for local synthetic
photo registration, including when the original counter wraps to zero. Two normal20 native reds
and targeted diagnostic logs establish that the first otherwise-zero tag prevents the original
cancel path from removing that receiver. The guard leaves non-synthetic registration behavior
and all rendering/input handlers unchanged. See the
[regression ticket](../../../.scratch/rich-messages/issues/51-first-photo-cancel-tag.md); corrected
normal APK compiles and focused cancel/retry and shared-consumer assertions pass, with six
inspected original captures. Broader native regression remains required.


`0022-rich-text-mentions.patch` projects response-local explicit mention identities into original
recursive `TL_iv.textMentionName`, preserving signed 64-bit IDs. Snapshot lineage privately
remembers immutable supported profiles after complete response validation. Histories, live update
envelopes and differences carry that response's users before original message application.
The renderer is unchanged. All 75 independently authored native mention codec cases and 28 existing photo codec cases
pass on the compiled normal APK; real-bot rendering/edit/restart remains separate acceptance. See
[ticket 52](../../../.scratch/rich-messages/issues/52-rich-mentions-native.md).


`0023-rich-photo-observation.patch` extends private diagnostics with schema-2 targets carrying
bounded allowed asset IDs. It observes a unique direct-root original rich photo through a live
edit and reports its actual asset ID, key and image state. Coordinates include original animated
top padding, text origin and block padding; layout interpolation and receiver fades reject.
Rich progress/icon are null because original public getters do not expose them. Schema 1 retains
its existing ordinary-photo path. Native geometry/guard/late-completion acceptance remains in
[ticket 53](../../../.scratch/rich-messages/issues/53-rich-photo-observation.md) and
[ticket 55](../../../.scratch/rich-messages/issues/55-rich-photo-late-completion.md).


`0024-local-custom-emoji.patch` adds the opt-in v4 neutral catalog and document lookup adapter.
It projects original ID-based ordinary/caption entities and recursive rich/button emoji leaves,
then resolves original Documents only on the original request path. Response-local dependencies
validate before publication; retained metadata supports original cached Documents without
preseeding the original memory/SQLite caches. Static WebP and VP9 WebM use the shared authenticated
complete-file transfer lifecycle. Reserved document DC -1 and layer127 thumbnail local ID 2
preserve separate logical/asset IDs and cache keys through original TL serialization. Offline
lookup failure releases only the failed callback owner without invoking null or retrying.

The eight-source patch applies to the normal23 input with zero fuzz/offsets and exact private
output matches. Scoped Python checks and collection pass for the independently authored batched
codec matrix; APK compilation, the actual codec results, rendering, transfer faults and original
resolver cold-restart recovery remain coordinator-owned acceptance. See
[ticket 58](../../../.scratch/rich-messages/issues/58-custom-emoji-native.md).

`0025-rich-button-observation.patch` adds private, bounded observations of canonical rich
buttons, their original drawn geometry and the original touch/callback/copy/disabled paths.
It correlates a single armed operation with its exact decoded object, process lifetime and
HTTP callback identity. It preserves upstream rendering and action handlers; the observer
does not synthesize a click or execute a callback. See the
[frozen interaction contract](../../../docs/development/rich-button-implementation-contract.md).
Source review, exact patch application and the complete contained offline APK build pass
(3 minutes 1 second, strict dependency verification and verified signature). Native acceptance
remains required before this patch establishes runtime behavior.
