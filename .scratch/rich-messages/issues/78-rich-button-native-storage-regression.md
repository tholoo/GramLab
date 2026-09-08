# Independently verify native rich-button storage provenance

Type: task
Status: claimed
Work state: prepared for coordinator review and native execution
Owner: rich-button-native-storage-regression worker
Blocked by: ticket77 implementation for green execution

Own this ticket and original probe sources under `clients/android/probes/rich-button-storage/`.
Keep Android-derived context within the GPL boundary and preserve applicable notices. Coordinator
owns compilation integration, guest execution, patch queue and shared docs. This task can prepare
independent fixtures and an actual-Android probe while ticket77 implements the storage seam.

Use real original message serialization, `MessageCustomParamsHelper`, native buffers and SQLite
write/load/reopen, with exact normal APK classes. Do not substitute fake Android/TL/storage classes
or count a source-pattern assertion as runtime evidence. If native loader initialization prevents
an independently runnable probe, report the exact missing prerequisite before broadening scope.

The agreed interface adds local `TLRPC.Message.gramLabRichButtonRevision` and
`gramLabRichButtonProvenance` fields. Positive revisions have bounded strict UTF-8 JSON containing
exactly schema1, revision and ordered occurrences with path and complete canonical button. Empty
occurrences are authoritative for button-free/ordinary replacement. `Params_v1` adds `FLAG_14`,
then trailing int64 revision and TL byte array. Observer `capture(message, canonicalMessage,
revision)` captures the same decoded response; `restore(message)` validates all topology before
binding final objects. No public bridge/private observation schema changes.

Specify independently authored row, inline and nested canonical paths with duplicate labels and
actions. Verify final object identities differ after actual storage load and bind to the correct
revision/path. A→B→A revisions remain distinct through write/load/reopen. Exercise incoming
authoritative provenance against old params reads, stale custom-only updates, empty metadata-only
shell reads, legacy absence, ordinary/button-free replacement and existing local fields.
Malformed UTF-8/JSON, duplicate members, truncation, over-limit extension, trailing bytes and
topology/count/path/action mismatch must not grant any partial mapping. Preserve a red on normal25
where the relevant missing behavior is observable; unimplemented fields are not a behavioral red.

Probe code may use reflection to inspect original observer identity bindings at this diagnostic
boundary, but must separately retain full serialized outcomes and exact reconstructed objects.
No fake input/effect success. Full public Android input/clipboard acceptance remains coordinator-owned.
Provide reproducible source/compiler/DEX hashes, exact invocation, expected output and observed
limitations. Do not launch a guest, Gradle build or full gate. Freeze a clean commit for review.


Coordinator clarification during independent review: malformed private extension bytes must be
ignored without throwing through the original message loader, retaining the complete original
message and stock parameters parsed before that extension, with no partial mappings. Existing
stock version/framing errors outside the added extension keep their original behavior. A metadata-
only shell retains valid provenance without binding objects; reordered JSON members are semantic
equals and must remain admissible. These controls are included in the independent native probe.


## Prepared probe and verification

Original GPL-2.0-or-later probe, compile script, app-process invocation and reproduction notes live
under `clients/android/probes/rich-button-storage/`. The only runtime collaborators are the original
normal APK classes, real Android context, original native buffers and original SQLite wrapper.
No fake Android/TL/storage classes or account/controller workers are introduced.

The `baseline` mode uses only stock normal25 APIs and must reach an actual SQLite close/reopen
before an unbound reconstructed object can establish the intended red. The `suite` mode prepares
25 behavioral cases covering the frozen metadata interface and the independent review corrections.
These are prepared cases, **not 25 observed passes**. The probe writes full original/reconstructed
TL bytes, SQLite parameter bytes and complete expected/actual binding records, then closes the DB.
Prerequisite failures exit 2; behavioral failures exit 1; only all selected case successes exit 0.
The coordinator's earlier identity06 red used SerializedData and does not replace this native
SQLite red or green.

Native initialization follows the original NativeGuardProbe's `System.load` and
`native_setJava(false)` memory recipe, with a genuine installed-package context obtained through
ActivityThread. The original ApplicationLoader is constructed and attached without onCreate,
then assigned as the original singleton because full TL serialization calls
`isAndroidTestEnvironment()`. No account, native_init, application lifecycle or input is started.
Actual initialization remains unverified until the coordinator runs the probe in the dedicated guest.

Verified preparation:

- Own `tools/dev android --offline` ran `compile.sh` against the unchanged normal25 classes jar
  and APK, using Java 17 `javac --release 8 -Xlint:all -Werror`, Android API 36 and D8 36.0.0.
  Compilation and DEX generation pass. The script verifies the original inputs did not change
  during compilation; they are compile-only classpaths and are not bundled into the probe.
- `tools/dev default --offline --command shellcheck` passes both owned scripts.
- `bash -n compile.sh`, `sh -n run-on-guest.sh`, and `git diff --check` pass.
- Reproduction commands and guest invocation are in the probe README. All resolved local input
  paths and hashes are retained in `.cache/rich-button-storage-probe-final/inputs.json`.

Final preparation SHA-256 values:

| Input/output | SHA-256 |
| --- | --- |
| Java source | `fcc378666ab2219d8a91795b332e7d491d11ca89baaac24e86379fc854e0e4af` |
| javac executable | `a34bbe66a2518337e41c587b82b4d2f75878f7862f4a0764bbcd7e18114ff777` |
| D8 jar | `4097ff9c46c185c6e7214da7fe9b1befb5adeea5cc9ca349270e0249904f9240` |
| Normal25 classes jar | `63f6f247b866e39cf0a6b42d92b403f3fd5dbfbe2f068eaa2aaaba2b6447f2ef` |
| Normal25 APK | `cb53bdc1eee3d6fa6848d82c78ca9143ed4dc75db329b8fec0ddf9a7ec142a49` |
| Probe DEX | `2f5035c2ab56bc5954ed0ecfd0294c26b8b7a0ef94ce449f74f8c276bc1e9e90` |
| Probe APK | `3630d68fbd5a7ea50be2af6334465609ff6729e051f6a2923fc557f1daae36ee` |

No guest, Gradle/full-source build, full gate or runtime network was used by this worker. The
coordinator owns native loader staging, baseline/green execution and public edit/restart/input
acceptance. This probe exercises original helper sequences with actual native SQLite; it does
not invoke asynchronous MessagesStorage/account controllers and cannot certify those entry points.
