# Deliver ordinary documents through the original Android loader

Type: task
Status: resolved
Work state: integrated and accepted; loader, cold-cache and UI105 native gates passed
Owner: coordinator
Blocked by: none

Implement the GPL adapter side of the [frozen document contract](../../../docs/development/documents-implementation-contract.md).
World99, Bot API102, v5 HTTP103 and codec101 are integrated. The codec's host checks and coordinator-run 34-case actual native gate pass. Preserve the complete operational scope; this is the next
single-document delivery slice, not completion of classification, edits, albums or the full goal.

## Ownership and dependencies

Own this ticket, new `clients/android/patches/0030-ordinary-document-delivery.patch`, its series
append, new `tests/test_android_document_delivery.py`, `tests/probes/android_document_delivery.py`
and GPL fixtures under `tests/fixtures/android_document_delivery/`. Keep production code entirely
within the existing Android GPL patch boundary. Do not edit Python core, existing tests, shared
contracts, runner selectors, lockfiles or dependencies. Report any required integration adjustment
to the coordinator. Use a private worktree and only minimal touched-source staging; no full source
copy/export, live build mutation, APK build or guest run. Coordinator owns native execution.

The patch may extend `GramLabMedia`, `GramLabBridge` and `FileLoader` at their existing synthetic
seams. Codec101's strict `GramLabDocument.Entry`, `parse` and `project` are fixed dependencies.
Reuse the existing response scope/epoch mechanism, original message/media classes and loader
callbacks. Do not fabricate image dimensions or adapt a document into an image Asset.

## Response and message application

Negotiate version5 explicitly and retain supported v4 behavior. Extend the response scope with a
distinct ordinary-document map and used-ID set; the existing map named documents contains custom
emoji and must remain separate. Install immutable ordinary dependencies before message decoding.
Reject changed metadata under an existing ID, missing dependencies, malformed/mixed carriers and
inconsistent bindings before publishing state. Snapshots may contain unused retained grants;
changes/callbacks must retain exact historical dependencies and frozen retry semantics. Keep
response validation/commit atomic, including users, images and custom emoji.

Map the canonical ordinary document message to the original `TL_messageMediaDocument` using
codec101 and existing caption entities/keyboards. Retain negative ordinary IDs and positive custom
emoji IDs at DC-1, including magnitudes2147483648 and9223372036854775807. Native adapters must not
interpret canonical decimal strings through a floating-point value or narrow integer.

Preserve original classification as well as drawing: pinned `MessageObject` recognizes image/gif
MIME as GIF even without specialized attributes. A typed ordinary descriptor therefore does not
promise TYPE_FILE for every MIME. Keep canonical MIME and original classification unchanged;
include a real native GIF classification control, and report its resulting original behavior.
Do not rewrite MIME or modify drawing/classification to force every payload into a file row.

## Original loading and destinations

Resolve both reserved Document and ImageLocation loading entry points locally before the original
Integer.MIN_VALUE filename guard or a remote queue. Known negative IDs fetch authenticated
`/v5/documents/D`; positive custom emoji keep their existing route and authority. Unknown reserved
IDs and streams fail locally. Include document-specific trace identity (`document_id`), never a
fabricated `asset_id`, and preserve credential redaction.

Validate exact declared length and SHA before publication; use octet-stream only as transport
fallback for empty MIME. Reuse bounded transfer cancellation, retry, progress, shared consumers,
cleanup and original notifications. Keep original saved-path lookup and cache-type destination
selection, including cache types0/10 and canSaveAsFile. Publish to the original sanitized filename
with original collision suffix behavior where applicable; persist the actual final destination in
FilePathDatabase. A concurrent same-name file must never be overwritten. Preserve keyed cache
destinations for the other applicable modes and handle stale saved paths through the original
semantics. Do not instantiate a remote FileLoadOperation just to borrow a helper.

The private bot adapter has no encrypted/secret-chat delivery implementation. An encrypted-cache
request must fail explicitly before writing, not create plaintext under encrypted-cache semantics.
Record that limitation; this task does not claim secret-chat or local encrypted-cache support.

## Acceptance and handoff

Prepare an actual native probe using original classes, with independently specified full outputs
and no replacement TLRPC/loader implementation. Cover valid v5 mixed responses, rejected-response
atomicity, missing/extra/changed dependencies, historical callback replay and unchanged v4 controls.
Cover both loader entry points and full-range IDs; exact bytes, wrong digest/length/truncation,
cancel/retry, coalescing, unknown IDs, local stream/encryption rejection, saved and missing paths,
concurrent equal filenames, persisted destinations, warm cache and cold restart. Original rows,
captions/custom emoji and keyboard callbacks need real UI evidence alongside complete World/API
state comparisons. Host substitutes may validate orchestration but cannot certify these behaviors.

Follow TESTING.md, licensing, offline safety and the parallel workflow. Run focused host checks,
strict typing, Ruff, Java/D8 compilation and minimal patch staging from the assigned checkout.
Keep red/green evidence and explain unavailable native checks honestly. Report stable probe inputs,
required native run plan and exact frozen branch tip; stop all owned processes before handoff.
Coordinator reviews/merges, builds and runs native acceptance, then enables the host's explicit v5
selector in runner, CLI and Android orchestration only after the delivery contract is verified.

Coordinator-approved narrow extension: patch0030 also changes only GramLabRuntime’s custom-emoji
request admission predicate to accept explicit versions4/5; every other predicate is preserved.


## Source-confirmed ordinary preload boundary

Cache type10 at or below 2 MiB retains the original full-file completion behavior and omits
initial UI loading registration; an ordinary coalesced request enables that registration.
Above 2 MiB it fails locally before HTTP or writing. Independent source review found that stock
cache10 is a video-only caller path: filename-only ordinary documents lack supportsPreloading,
so the stock large-file path has no preload stream and fails on its first data response. The
coordinator therefore confirmed local unsupported behavior, without inventing generic preload
or a Range protocol. Native boundary acceptance must still prove both entrypoint rejections,
zero HTTP/UI/files/sidecars and a normal successful retry of the same oversized descriptor.
The ticket remains in progress until the actual delivery/UI gates are completed.


## Atomic publication capability checkpoint

Actual target-process filesystem diagnostic07 reached the original writable external-files directory.
Both Java createLink and Os.link failed with access denial (EACCES13); this rules out the draft
hardlink publication on the actual profile. Sequential Files.move rejects an occupied destination,
but that does not establish race-safe no-replace behavior. Production remains unchanged pending a
supported atomic primitive; no replacement rename, final-path copy or destination workaround is allowed.

Coordinator approved a fixture-only JNI capability check using cached NDK27.2.12479018, compiled
for all four Android ABIs at API26. It calls syscall(SYS_renameat2, ..., RENAME_NOREPLACE) directly,
returns exact errno and has no fallback. Bounded byte-array paths preserve UTF-8 including non-BMP
characters and reject null/empty/embedded-NUL/oversize inputs. Native acceptance checks absent and
occupied destinations, missing source, invalid paths, Unicode names, and eight two-contender races
with one complete winner and unchanged loser. Only the actual x86_64 target guest can prove runtime
support; other ABIs are compile/ELF evidence only. Any production JNI extension awaits that evidence
and explicit coordinator review. Instrumentation05 and all prior diagnostic sources remain frozen.


Coordinator-authorized production extension: patch0030 now includes only the existing
`TMessagesProj/jni/TgNetWrapper.cpp` JNI file in addition to the four Java files. Actual rename01
on the original target app's x86_64 external mount passed absent/Unicode publication, occupied
EEXIST, missing ENOENT, invalid EINVAL, and eight complete-winner races with both winning orders.
This supports the bounded API26 syscall primitive, not other-device runtime claims. The loader
uses UTF-8 bytes and retries collision suffixes only on EEXIST; every other errno fails locally.
Image/custom-emoji publication is unchanged. The full native suite must exercise the original
FileLoader JNI method from the built production APK, independently of the diagnostic library.


## Worker verification checkpoint

The current five-file patch applies to the normal29 baseline with exact before/after hashes.
All four staged Java classes and the complete original TgNetWrapper translation unit compile;
the latter uses the original API21 command, while the diagnostic syscall also compiles at API26
for all four ABIs. The signed instrumentation passes javac/D8/NDK/signature checks. Host verification
is35 passes; the preceding red retained the rejected legitimate alternate race winner (1 failed,
34 passed), corrected by allowing only the two exact single-winner errno pairs. Strict typing,
Ruff check/format, shell syntax/ShellCheck and Android collection (one selected test) pass.

The implemented production path and full35-case suite plus cold-process cache have not yet run
on a rebuilt application. Coordinator owns that build, native execution and separate UI105 gate.
The branch is an implementation handoff, not closure of the ticket's native acceptance.

## Coordinator integration checkpoint

The reviewed frozen branch is integrated. All41 affected host cases pass together under the
offline namespace, including the document scenario and codec controls; strict typing, Ruff and
shell checks pass. JUnit is retained as `artifacts/document-delivery-integrated-01.xml`.
A bounded reconstruction from the pinned upstream revision reproduces all29 prior patches and
the sanitized preparation input across40 source paths. Every cached byte matches, including the
five patch0030 preimages; coordinator private staging then matches every expected postimage.
The complete ordered patch identities will be bound into the new APK source record.
Production native and original UI acceptance remain pending; this ticket is not resolved.

## Native timeout diagnostic follow-up

The coordinator's production native02 launched normal30 but its original suite instrumentation
exceeded the unchanged240-second deadline. No case summaries were pulled, and the old archive
record retained only returncode1, so no initialization/queue/case cause is established yet.
Production remains frozen. The fixture now emits immutable initialization and case-start/completion
records into a separate allowlisted diagnostic root without consuming the fresh suite directory.
A daemon watchdog starts before attachment/native initialization and records at most eight
30-second samples, each bounded to48 threads, eight frames per thread and128 KiB. Phase/stage and
completion counters are thread-visible. It observes actual original thread stacks and performs no
retry, case selection or deadline extension. Successful instrumentation result framing is unchanged.

The host retains bounded redacted timeout partial output and archive/retrieval return codes and
stderr. Packing uses an app-owned file and includes every present allowlisted root; retrieval
bounds compressed bytes before base64, validates encoding/size, then uses the existing strict
archive parser. Retention errors never replace an original native exception. Host regression red
proved missing timeout evidence and masking by a subsequent archive timeout; real POSIX tools
exercise the new shell framing, but host permissions do not establish Android permissions.
Actual instrumentation08 evidence must locate the blocked stage before selecting smaller cases
or considering any production correction. All prior probes/native failures remain retained.


Follow-up verification: the initial focused host red has2 failures (lost timeout output and
archive timeout replacing the original exception). Final focused checks pass44, including real
POSIX tar/head/base64 transport, exact diagnostic bytes, malformed/overflow rejection and timeout
redaction/identity. Strict typing, Ruff check/format and Android collection pass. Instrumentation08
compiles/signs against the coordinator-built normal30 using cached javac/D8/NDK tools; its exact
sources/manifests are retained separately from07. Binary retrieval status retains only encoded
length/SHA, returncode and bounded stderr, not a duplicate opaque base64 payload. No production
patch, native deadline, input or case order changed; actual native diagnosis remains pending.

## Integrated diagnostic result

The diagnostic follow-up passes44 integrated host cases and scoped strict typing/Ruff; core19
passes all1,192 cases at88.11% coverage. Native03 on unchanged normal30 reaches32 completed cases
within about2.1 seconds:31 pass, while v5_emoji_and_ordinary_namespaces fails with
NoClassDefFoundError for AndroidUtilities through SharedConfig initialization. Its recorded cause
is ExceptionInInitializerError without the original nested cause. Case33, cache10_exact_boundary_and_upgrade,
then blocks in FilePathDatabase.getPath's latch through FileLoader.loadOrdinaryDocument. Seven
watchdog samples retain the same stack, with no database queue thread among the19 observed threads.
The240-second deadline still fails. Archive packing/retrieval now both return0 and exact diagnostics
are retained. These partial results do not close native delivery or cold restart. Investigate the
first initialization cause and reduced fixture prerequisites before a production correction.

## Fixture initialization follow-up

The `task/document-delivery-fixture-init` worker owns the fixture-only correction. Acceptance is
limited to mirroring production's validated-context initialization order for `AndroidUtilities`,
capturing at most four throwable levels and four frames per level with cycle detection and
`ExceptionInInitializerError.getException()` precedence, and draining the original
`FilePathDatabase` queue through an eight-second barrier that always releases its latch and surfaces
the originating `Throwable`. The normal30 production APK/patch, native deadline, case order and
oracles remain unchanged. Host regressions must fail before the correction; focused host, strict
Python and fixture javac/D8 checks must pass. Android execution remains coordinator-owned.

The worker's three focused regressions first failed on the unmodified fixture: there was no
AndroidUtilities initialization call, no recursive throwable serializer, and no immediate
FilePathDatabase initialization barrier. After the fixture-only correction, all47 non-Android
document-delivery checks pass. Strict mypy passes for the test and its imported probe; Ruff lint
and format checks pass. Javac with warnings as errors and D8 pass against the unchanged normal30
compile classes (`2e61edd1d92c9a339c7da9ac836619b0fb0c8cb32b0def91ceb28e978a4381ea`)
and APK (`a964bbaccaaf59719d966a72ecd85de4288d146887e3f7ff7d50be7281df726b`).
The compiled fixture source is
`1347d528f0268fe8c2538bc100b62664e23dc6a2a89e9290c482b6c79ec60c42`, and the
resulting DEX is `119668fd7063fd7f6c52c0eb6df9d6186d59900cf3b2d6e365a3279d266e534c`.
No production patch, after-hash manifest, case/oracle, deadline, Android build or guest run changed.
Actual native delivery and UI acceptance remain pending coordinator execution.

## Native delivery acceptance

Coordinator native04 and native05 reproduced the same target-process crash after34 passing cases;
native05 had no overlapping UWB bugreport or dumpstate work, ruling out that environmental theory.
Native07 added bounded final-case checkpoints plus crash-buffer and package exit-reason retention.
It located the failure inside the original `MessageObject` constructor, before either document
request: Telegram's scheduled transcription callback reached patched
`ConnectionsManager.getCurrentTime`, and `GramLabRuntime.now` correctly rejected the fixture's
missing runtime snapshot with `GRAMLAB_NOT_INITIALIZED`. Android retained reason4
`APP CRASH(EXCEPTION)`. The production application path was not defective.

The fixture now mirrors that suppressed `ApplicationLoader.onCreate` prerequisite immediately
before original message construction: it serves the exact current loopback v5 snapshot, invokes
the unchanged public `GramLabRuntime.initialize` path, verifies the frozen world time and deletes
the secret-bearing temporary configuration before archive packing. It does not weaken the runtime
guard, patch production, extend a deadline, select a favorable subset or add external network.
Host regression tests first failed for missing case boundaries, crash retention and runtime
initialization. Final non-Android document verification passes49 cases with strict mypy and Ruff.

Native08 passes the complete35-case target-instrumentation suite and the separate one-case cold
process on unchanged normal30 APK
`a964bbaccaaf59719d966a72ecd85de4288d146887e3f7ff7d50be7281df726b`.
Suite PID2303 records35 passed,0 failed and54 exact authorized loopback requests; final collision,
original JNI no-replace publication, persisted destination and same-process database checks pass.
Restart PID2441, under the same UID, records1 passed,0 failed, zero HTTP and reads both saved
destinations from original SQLite. External IPv4/IPv6 probes fail with `Network is unreachable`,
and the host namespace exposes only loopback. JUnit and complete bounded evidence are retained in
`artifacts/document-delivery-native-08/`; its input record SHA-256 is
`cc7572b936c40bf4c503dafb59c4e66debdb9a6aada6ccb88f8ff347fad4bd7b`.
The signed fixture source/DEX/APK hashes are respectively
`77090565d4e6771a6dc803b2a86dce15f9a6040a60a9658fc33f155f2a3e5ccb`,
`2a22820b297efd8d5e1034a7cd7e396e8c084799d088633cfe1a481f438fdafe` and
`1a19b889cc5987d1676557fa33dba4bbdef5e533a163d72a7bc62d0aa7b330c3`.
Ticket105's original LaunchActivity rendering, interaction and UI restart evidence now passes in
native10. This resolves the ordinary-document loader/UI slice; default classification, albums and
the broader operational milestone remain separate.
