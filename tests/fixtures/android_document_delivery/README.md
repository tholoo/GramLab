# Original document delivery probe

The Java fixtures are GPL-2.0-or-later diagnostic code in the Android adapter boundary. They use
the pinned original APK classes, native libraries, NativeByteBuffer, FileLoader, FilePathDatabase
and actual target app UID. Only the explicit loopback HTTP peer substitutes for the private bridge
service. This is not a World/Bot API run or original UI rendering proof; ticket105 owns those gates.

## Build and stage

Compile the tiny target-package instrumentation APK with existing pinned local tools and the
same dedicated debug signing identity as the coordinator-provided original APK:

```sh
tools/dev android --offline --command bash \
  tests/fixtures/android_document_delivery/compile-instrumentation.sh \
  "$ORIGINAL_CLASSES_JAR" "$ORIGINAL_APK" "$DEBUG_KEYSTORE" "$NEW_PROBE_OUTPUT"
```

This uses javac, D8, aapt2, zipalign, apksigner and the cached pinned NDK for the tiny capability
library; no Gradle, new dependency or original APK build.
The output is create-only. Its inputs manifest binds all Java/C sources, manifest, both scripts,
compiler/platform tools, original class JAR/APK, DEX and signed probe APK. Target and probe signer
certificates must match. Debug key locations remain ignored; no release signing is authorized.
`compile.sh` alone produces a standalone diagnostic DEX/APK, not the acceptance instrumentation.

Verify patch applicability without modifying the source:

```sh
tools/android-patch-stage --source "$ORIGINAL_PATCHED_SOURCE" \
  --patch clients/android/patches/0030-ordinary-document-delivery.patch \
  --before-sha256 tests/fixtures/android_document_delivery/before-sha256.json \
  --after-sha256 tests/fixtures/android_document_delivery/after-sha256.json \
  --output "$NEW_PRIVATE_STAGE"
```

The before manifest describes series through0029 at ticket104 base
`03bb98d1c0eab9e74aa46adebc5d04b85eae9714`; the after manifest binds four touched Java files and the single existing TgNetWrapper.cpp JNI
file. Staging copies only those five files. Compile a new probe output after any fixture source change.

## Coordinator-owned native execution

```sh
GRAMLAB_ANDROID_RUNTIME_PROFILE="$PROFILE" \
GRAMLAB_ANDROID_PROBE_APK="$ORIGINAL_APK" \
GRAMLAB_ANDROID_DOCUMENT_DELIVERY_PROBE_APK="$NEW_PROBE_OUTPUT/probe.apk" \
GRAMLAB_ANDROID_DOCUMENT_DELIVERY_PROBE_INPUTS="$NEW_PROBE_OUTPUT/inputs.json" \
  tools/dev android --offline --command .venv/bin/pytest -q \
  tests/test_android_document_delivery.py -m android
```

The bootstrap installs the exact original APK and test-only instrumentation APK, then invokes
`am instrument -w -r` once for the suite and once for cold-process cache acceptance. Android supplies
the real target Application and Context; public APIs verify object identity, package, UID and
AttributionSource. No hidden-API exemption, target SDK change, privileged filesystem operation or
substituted destination is used. The probe records groups, SELinux context and mount fingerprint.

The instrumentation deliberately suppresses `callApplicationOnCreate`, retaining the actual
original Application object. After validating and installing the target Application/Context, it
invokes the original `AndroidUtilities.getHelloWorld()` initialization hook before NativeLoader,
matching the ordering in production `ApplicationLoader.onCreate`. The first fixture-created
FileLoader initializes its original FilePathDatabase on that database's own queue through an
eight-second barrier; the barrier catches every Throwable, always releases its fixture latch and
rethrows the original Exception or Error on the instrumentation thread. It then initializes
original NativeLoader and native_setJava(false), without accounts, native_init or full application
lifecycle. Before the sole original `MessageObject` construction, the fixture serves the exact
current local snapshot and invokes the original public `GramLabRuntime.initialize` path. This
mirrors the production prerequisite for main-thread time callbacks; the secret-bearing temporary
configuration is deleted before evidence packing. This is explicitly recorded in runtime evidence.
The separate UI gate runs normal LaunchActivity initialization and drawing. The second
instrumentation invocation must have a different PID under the same UID and read saved paths from
original SQLite without new HTTP. It does not stand in for the full UI restart/cache gate.

Initialization and case diagnostics retain a redacted throwable chain of at most four levels and
four frames per level. `ExceptionInInitializerError.getException()` is followed before the ordinary
cause, cycles are marked without recursion, and the existing 128 KiB diagnostic-record bound still
applies.

The independent Python oracle specifies all35 suite cases, ordered HTTP effects, immutable
metadata, full signed-ID boundaries, caption/entity/keyboard outputs and the cold-process result.
Cases cover response atomicity, historical callback retries, v4 regressions, v5 send, authority
rotation, both loaders, wrong bytes/length/MIME, cancellation/retry/coalescing, caches, actual external
filename collisions and persisted paths. GIF classification is checked through the original
predicate; that alone does not prove GIF decoding or pixels.

The bootstrap requires exact platform result framing and success code, retains failed output,
and never starts the cold process after a failed suite. Pulled summary JSON must equal original
instrumentation output. Limits:1 MiB per output stream,4 MiB compressed archive,16 MiB expanded,
and512 members. Unsafe/duplicate/link/secret-bearing/parent-conflicting archives fail before
extraction. Each native invocation has240 seconds inside the existing600-second isolated deadline.
No favorable subset can satisfy the native oracle. A platform `Process crashed` result also retains
bounded, redacted crash-buffer and package `ApplicationExitInfo` output before archive retrieval;
failure to collect either diagnostic never replaces the original framing failure.

For filesystem diagnosis on the unchanged baseline APK, install the signed probe with `install -t`
and run the same component with `-e mode filesystem`. It retains the real getExternalFilesDir root,
state and concrete exception before failure. The output directory must be fresh. A successful
diagnostic means it executed, not that a reported unsupported primitive can publish files.
Standalone `identity` mode uses a separate `files/document-delivery-identity-probe` directory and
records the run-as process context without consuming the filesystem probe's directory.

## Supported boundaries and source evidence

Encrypted cache and local streams fail locally; no secret-chat/encrypted-cache implementation is
claimed. Cache10 at or below2 MiB keeps original full-file completion without initial loading UI;
a normal coalesced request enables UI. Above2 MiB, filename-only ordinary documents fail locally.
Both entrypoints must produce a failure callback with no HTTP/UI/final/temp/sidecar creation, then
permit a normal successful download of the same descriptor.

At Android pin `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`, FileLoadOperation.java165 defines the
threshold,435 enables preload only for a video attribute,1063 gates opening that stream,1307 handles
the small-file no-op, and1861 uses the stream. PhotoViewer.java16489–16494 calls cache10 behind
stream/video admission. Inventing generic ordinary preload or Range behavior is outside this task.
Canonical MIME and original classification, including GIF/MKV predicate edges, remain unchanged.
These source observations do not replace actual native boundary evidence.

Standalone filesystem diagnostics01–03 failed in framework package/UID attribution before touching
file primitives. Diagnostic04 confirmed the initial-Application correction;05 then established an
AccessDeniedException at the actual mounted external-storage path. Instrumentation diagnostic06
exposed target-process filtering of a hidden identity method. The corrected target instrumentation
uses only public identity APIs. Diagnostic07 reached the real writable external root and proved
both hardlink APIs fail with EACCES13. Its sequential Files.move control does not prove race-safe
publication. All prior native evidence remains retained; complete delivery remains unproven.

Pinned public Android16 source reference: frameworks/base `android-16.0.0_r1`, commit
`99b01a65cc4c104933788b3143285ab6bae65827`. ContextImpl894 → Environment.UserEnvironment187/230 →
StorageManager1438 uses ActivityThread.currentOpPackageName2920 and mInitialApplication3233;
StorageManagerService3927 rejects caller-package/UID mismatch. System/core run-as at
`68be0c2c0006a0740d0b1809abe4717308f90d15`235–242 changes UID/GID/groups and SELinux to fromRunAs,
without requesting a target app mount namespace. These are pinned public source references, not
claimed exact source builds of the retained BE2A image. Raw sources and hash manifests stay ignored;
no framework implementation is copied into the diagnostic.


## Fixture-only no-replace rename capability

Use the same instrumentation component with `-e mode rename` on a fresh target data directory.
The signed probe includes a tiny JNI library for x86_64, x86, arm64-v8a and armeabi-v7a; it is loaded
only in this diagnostic mode. Original production libraries and the delivery patch are unchanged.
The check uses the actual getExternalFilesDir root and the same public Application/UID assertions.
Source, compiler, ABI/ELF output, header and library hashes are included in inputs.json.

Pinned NDK27.2.12479018 stdio.h178 defines RENAME_NOREPLACE; its libc renameat2 declaration at201
requires API30. The fixture instead compiles the existing syscall ABI at API26 using SYS_renameat2,
with no dependency on the newer libc symbol. Exact unsupported-kernel/seccomp/filesystem failures
are retained; no copying, replacing rename or alternate destination is attempted. The byte-array
JNI boundary limits paths to4095 bytes and rejects embedded NUL, preserving ordinary UTF-8 rather
than JNI modified UTF-8. Cases include a non-BMP destination, occupied EEXIST, absent success,
missing-source ENOENT, invalid EINVAL and eight synchronized two-source races. Each race must leave
exactly one complete winner and the complete unsuccessful source. These runtime controls establish
capability on the tested external mount; four-ABI compilation does not establish other devices'
runtime support. Production adoption requires coordinator review after the actual diagnostic.


The coordinator's actual rename01 passed on the original target app's x86_64 external mount:
absent and non-BMP publication returned0, occupied17, missing2, invalid22; all eight races had
exactly one complete winner and an unchanged loser, with both winning orders observed. Other ABI
runtime support remains unproven. Production patch0030 now adds the equivalent bounded primitive
to the existing TgNetWrapper.cpp and invokes it only for ordinary documents. Collision suffixes
retry only EEXIST; all other errors fail closed. Existing image/custom-emoji publication is unchanged.
The original native translation unit also compiles with its existing API21 flags, without the
API30 libc dependency.

The full suite's `production_document_rename` case invokes the actual original FileLoader native
method from the installed production APK by reflection. The fixture library is loaded only in
`rename` diagnostic mode, never in the production suite. The same independently authored controls
exercise the production method, and the Python oracle requires its implementation marker plus
all error/Unicode/race observations. Successful diagnostic-library evidence cannot satisfy this
case. The production35-case suite plus renewed-process cache and separate UI105 gates remain pending.
