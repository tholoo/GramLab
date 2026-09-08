# Native rich-button storage regression probe

This original GPL-2.0-or-later diagnostic links against the normal Android APK's actual classes.
The applicable license is [the Android adapter GPL text](../../patches/COPYING). No upstream
implementation or generated classes are included here. The root MIT license does not relicense
this adapter-bound diagnostic.

The coordinator executes it inside an already contained, dedicated guest. Compilation alone
establishes API applicability, not successful Android initialization or storage behavior.
No guest, account, application lifecycle, input action or network service is started by these
host preparation scripts. The guest entry initializes the genuine Android system looper and
installed-package context, constructs and attaches the original `ApplicationLoader` without
calling its lifecycle, loads the exact APK's native library, and calls `native_setJava(false)`.
The original application instance is necessary because full message serialization calls its
`isAndroidTestEnvironment()` method.
It does not call `ApplicationLoader.onCreate` or `native_init`.

## Compile without Gradle

Enter this checkout's pinned Android shell and supply its already built, reviewed inputs:

```sh
tools/dev android --offline --command bash \
  clients/android/probes/rich-button-storage/compile.sh \
  /absolute/path/to/normal-client-classes.jar \
  /absolute/path/to/matching-normal-client.apk \
  .cache/rich-button-storage-probe-RUN
```

The output directory must not already exist. The script compiles only this original probe with
Java 8 bytecode, Java 17 `javac -Xlint:all -Werror`, Android API 36 and D8 from build tools 36.0.0.
The original classes jar is a compile-only classpath; only probe classes go into the generated
DEX/APK. At runtime the approved normal APK supplies every Telegram/Android collaborator.
`inputs.json` records source, compiler, D8, Android API, original classes/APK and generated DEX/APK
SHA-256 hashes and the compiler version. Keep it with the run's original APK/native-library hash
and evidence. The source has no direct references to new fields, so it also compiles against
normal25; the full suite resolves ticket77's frozen interface reflectively.

## Coordinator guest invocation

Install the reviewed normal APK and stage the generated probe APK, the matching original APK,
its original ABI-specific `libtmessages.49.so`, any original native loader dependencies, and
`run-on-guest.sh` under a dedicated app-private staging directory. Files must be owned by the
installed app UID; mark APK/DEX inputs read-only before `app_process` loads them. The application
must be installed so the genuine `createPackageContext` can resolve its files directory.
Preserve the existing outer network/process containment and guest lock.

As the installed `org.gramlab.android` UID, invoke:

```sh
sh /data/user/0/org.gramlab.android/files/storage-probe-stage/run-on-guest.sh \
  /data/user/0/org.gramlab.android/files/storage-probe-stage/probe.apk \
  /data/user/0/org.gramlab.android/files/storage-probe-stage/client.apk \
  /data/user/0/org.gramlab.android/files/storage-probe-stage/libtmessages.49.so \
  /data/user/0/org.gramlab.android/files/rich-button-storage-RUN \
  baseline
```

The output directory must be absent, must be directly beneath the actual installed app's files
directory, and must start with `rich-button-storage-`. The probe creates its own `probe.db`; it
never opens the application's account databases. Use `suite` for the patched APK. Use fresh
output paths for every invocation. The coordinator owns staging, invocation, collection and
cleanup; this directory contains no automatic ADB launcher or guest reset.

Initialization emits `android_context`, `native_library`, `sqlite_open`, then `behavioral_cases`.
An initialization failure exits **2**, emits `prerequisite_failure` with its phase and exception
classes, and is not a regression red. Missing ticket77 interfaces in `suite` are likewise a
prerequisite failure. The process explicitly closes SQLite and exits, avoiding lingering original
library threads. Exit **1** means at least one behavioral assertion failed; **0** means every
selected case passed. Preserve the per-case JSON before interpreting either result.

## Independent expected behavior

`baseline` performs one case using stock APIs available on normal25: native serialization of an
original rich `TL_message`, real original SQLite write/load/close/reopen, and reconstruction through
original `TLdeserialize` plus `MessageCustomParamsHelper.readLocalParams`. Six original objects
must initially be bound; their reconstructed identities must all differ. The expected normal25
red is `loaded_object_unbound_0` after those controls pass. A missing Java field/method, failed
native load, missing context, broken fixture, or altered TL bytes does not establish this red.
The previous coordinator identity06 result concerns `SerializedData` alone and is not a substitute
for this native SQLite result.

`suite` additionally captures the exact canonical message and revision using ticket77's interface
and prepares **25 total cases**, including baseline:

- Metadata-only serialization; exact independent FLAG_14 wire template; reordered JSON members; preservation of existing
  voice/language/star/summary/translated-rich fields.
- Six explicitly selected occurrences: two duplicate row buttons, wrapped inline text, details
  summary, nested quote paragraph and quote credit. Expected paths are independent literal arrays,
  including summary-before-blocks ordering, despite TL details serializing blocks before title.
- A → B → A through actual SQLite close/reopen, with distinct revisions and identical A content.
- Fresh incoming metadata versus old/legacy parameters; stale custom-only copy versus the current
  row's metadata; metadata-only shell reads without invented object bindings.
- Ordinary and button-free replacements retaining authoritative empty occurrence lists; legacy
  messages without provenance remaining unbound.
- Invalid UTF-8/JSON, duplicate members, over-limit payload, truncation, binary/JSON trailing data,
  conflicting revisions, missing occurrences, final-path/action mismatch and extra native topology.
  The independently serialized valid wire case controls the negative wire fixtures. A malformed
  private extension must preserve the original message and preceding stock language field without
  throwing. All original loaded objects remain unbound, including earlier valid occurrences before
  a final mismatch. Stock errors outside the added private extension retain their original behavior.

Per-case artifacts retain full original and reconstructed TL bytes, actual SQLite custom-params
bytes, complete expected/observed binding fields, runtime classes and process-local identity
hashes. Identity correctness uses Java reference comparisons, not hash equality. `summary.json`
records actual counts; there are no synthesized native success results. The probe retains its
SQLite file after close for independent inspection. Artifact size is bounded by these fixed cases
and the single 1 MiB + 1 payload control; no supplied capabilities/configuration are recorded.

This exercises the original helper sequences and actual native SQLite boundary. It does not
instantiate `MessagesStorage` account workers or call their asynchronous controller entry points.
The coordinator must review those entry points and execute the public native edit/restart flow.
No observation freshness, touch, callback, clipboard or rendering acceptance follows from this
storage probe, even when all its cases pass.
