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
