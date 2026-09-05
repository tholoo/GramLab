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

**The application is deliberately disabled.** The queue is not yet an offline client implementation.
Do not enable or install it to claim synthetic startup: Java/background networking, identity and
local bridge adaptations still have to be implemented and tested.

Preparation exports only pinned tracked files, removes upstream signing/service templates and
replaces the upstream API/hash/key fields with inert values. Their original values are not copied
into this patch queue. No personal configuration from ignored upstream files is exported.
No network request is made by preparation itself; dependency provisioning is a separate step.
Preparation also installs the committed dependency checksum record for strict Gradle verification.

Current verification and remaining compilation/runtime gates are in the
[build record](../../../docs/development/android-build.md). Continue to audit initialization,
native transport, media, WebViews, push and background networking together before activation.
