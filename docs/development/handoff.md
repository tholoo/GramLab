# Next-agent handoff

## Objective and authorization

GramLab runs real local bots against one SQLite World and uses the actual Telegram Android
renderer. The isolated bot → Android → tap → callback → bot edit → restart loop is proven.
Simulation and Android share semantic state; only Android supplies rendering/input evidence.

The full [product inventory](../product/requirements.md) remains the goal. The
[first operational milestone](operational-milestone.md) requires messages/buttons, rich content,
photos/files/albums and custom emoji in representative consumer workflows. Mini Apps are deferred
from that milestone only. Interactive mode and broader API/recovery/reporting remain unfinished.

The user approved the Android foundation and all four media/custom-emoji/mention/rich-button
designs, and resumed implementation. Follow [ADR0005](../adr/0005-local-media-and-client-interaction-boundaries.md)
and their frozen contracts. Local worker branches, coordinator merges and commits are authorized.
Keep runtime offline, use synthetic identities and zero real accounts, and preserve upstream
rendering. Consequential design, fidelity, licensing, runtime network and publication changes
still require consultation. The [automatic rich-detection policy](rich-auto-detection-proposal.md)
was submitted separately and remains unapproved; elapsed time is not approval.

## Accepted integration checkpoint

Core17 passes all **1,129 non-Android tests at 88.02% coverage**. Static16 passes all **65 documented
commands** and configuration/links in 262 Markdown files. Typed document World99, multipart100,
codec101 host checks, Bot API102, v5 client HTTP103 and atomic World creation13 are resolved.
The reviewed scenario105 is also integrated; its native acceptance remains pending. [Documents](documents.md) records the implemented forced-file HTTP profile and limits.

Normal29 contains the ordinary codec but does not enable document delivery. All34 actual codec
cases pass in native04 on that APK; the identical corrected probe rejects normal28 specifically
for its absent codec class in native05. The probe uses original VM binding and native buffers.
The normal29 source/APK/probe identities and run evidence are retained in ignored local notes.

Core14's obsolete patch-order assertion and core15's runner-readiness assumption now have
specific corrections plus the green combined gate. Preserve the original failed JUnits.
The native01 status137 remains unexplained. Codec native02/03 exposed a standalone fixture's
missing VM binding, corrected without changing the production codec. A passing later run does
not establish the cause of an unrelated earlier failure.

## Active work and next actions

1. Review [104: original document delivery](../../.scratch/rich-messages/issues/104-ordinary-document-native-delivery.md)
   is reviewed and integrated with 41 affected host checks, strict typing and Ruff passing.
   Source reconstruction matches all 29 prior patches; private staging verifies all five changed
   files. Build normal30 next, then run the 35-case original loader suite and cold restart. Preserve distinct
   document/emoji identities, exact v5 dependencies, rejected-response atomicity, original
   destinations, cancellation, cache and notifications. Review found same-world authority rotation,
   cache10 lifecycle and missing v4/v5 native controls. Corrections are prepared; the publication
   primitive is now replaced in the integrated code; actual production/native acceptance is pending.
2. Actual target-process filesystem07 now establishes the publication blocker: app external files
   are writable, but Java and Os hard-link creation both fail with access denied. The original
   draft therefore cannot publish downloads there. A sequential Files.move control rejects an
   existing destination but does not establish race safety. A narrow atomic no-replace
   rename primitive was then verified in rename01: absent/Unicode targets succeed, an occupied
   target returns EEXIST unchanged, and eight two-source races retain exactly one complete winner
   and the unchanged losing source. Invalid/missing paths reject. The integrated patch uses this
   bounded UTF-8 syscall primitive in the existing GPL JNI library; the production loader
   suite and new APK remain pending. Runtime evidence is limited to the pinned x86_64 guest.
   Earlier standalone probes used a different process/storage context; target instrumentation suppresses Application.onCreate explicitly,
   verifies public Context/Application identity and retains zero-account/isolation evidence.
   Filesystem06 failed on hidden-API reflection; public-API-only instrumentation05 passes07.
   Preserve all original source/results; diagnostic success is not document-delivery acceptance.
3. Source/caller review corrects the cache10 interpretation: ordinary filename-only documents do
   not enable the original video preload stream. Above2MiB, the original path fails on its first
   nonempty response; the stock caller targets video, with an MKV MIME edge. Preserve explicit
   local rejection for ordinary files, both loader entrypoints, zero requests/UI/files and normal
   retry; keep the original small-file behavior. Those native controls remain pending. A generic
   document preloader or Range protocol is not required to reproduce this unsupported boundary.
4. [105: real-bot document UI](../../.scratch/rich-messages/issues/105-ordinary-document-native-ui.md)
   is reviewed and integrated. Its three host cases pass on the current World, with strict typing
   and Ruff. They cover the full contained real-bot scenario, bounded failure evidence and complete
   ordered APK input binding. Corrected launch/restart phase accounting and original named-file
   destination assertions are included. Native execution remains pending104 and a normal30 APK.
5. Merge only reviewed frozen delivery/edit branches, run affected checks, and build using the
   existing incremental cache. Enable the host's explicit v5 selector only after delivery passes.
   Capture original rows/captions/emoji/keyboard, actual download/callback actions, exact destination
   bytes, phase-local GETs, warm reuse, cold restart and complete matching World/API state.

Independent [106: standalone media edits](../../.scratch/rich-messages/issues/106-standalone-media-edits.md)
is back with its worker after review found a false edit for already-empty captions and incomplete
full-state/boundary assertions. The worker is retaining that actual regression before correcting
comparison semantics and strengthening coverage. Earlier90 affected checks are not acceptance of
those missing cases. An eight-case retrospective baseline run proves absent-operation sensitivity;
it does not replace the missing pre-implementation red. Integration and native acceptance remain
pending; albums and other unsupported forms remain separate.

[107: public runner v5](../../.scratch/rich-messages/issues/107-document-runner-v5.md) is assigned
independently. It covers explicit selection, ordinary document callbacks and rich-button checks in
mixed-content worlds. Its integration is gated on104 native delivery; default3 and explicit3/4
behavior remain unchanged.

After this batch, required operational work still includes default upload classification,
media/document edits, albums, approved automatic rich detection, wider rich-button placement/
recovery and representative combined workflow/current-APK regression. Preserve the full inventory;
an explicit unsupported error is an honest intermediate state, not completed compatibility.

## Existing evidence to reuse

Read the [compatibility matrix](../compatibility/matrix.md) and the relevant task before claiming
support. Focused original evidence exists for structured rich/RTL blocks, explicit links/mentions,
PNG/JPEG lifecycle and faults, static/animated custom emoji, and callback/copy/disabled actions.
Those scenarios use different recorded APK checkpoints; they do not replace the latest full gate.

When investigating an earlier result, read the preserved
[core16 handoff snapshot](handoff-checkpoint-core16.md) and its linked tickets. Older history is in
[handoff-history.md](handoff-history.md). Their next-action statements are historical. These preserve
red/green evidence, import-contaminated runs, retained original captures and exact scope limits.

## Efficient execution and retention

Follow [AGENTS.md](../../AGENTS.md), [TESTING.md](../../TESTING.md), [offline safety](offline-safety.md),
[parallel work](parallel-work.md), [CONTRIBUTING.md](../../CONTRIBUTING.md) and
[completion requirements](completion.md). Workers use separate branches/worktrees/environments;
root owns shared docs, merges, conflicts and combined verification. Bounded routine tasks may use
GPT-5.6 Sol. Consult actual agent/process handles after resumption before restarting anything.

Use the assigned checkout's tools/dev and verify its editable import resolves there. Inherited uv
environment targets previously invalidated checks. Share only verified immutable inputs; retain the
current incremental Android build. Core uses four isolated workers. Android guests remain serial
under android-gate; builds hold android-build. Parallel guest scheduling is unaccepted. Use focused
checks during development and rerun combined gates only after relevant changes or failures.

Keep host paths, proxy settings, process handles, APK pointers and raw performance samples in
ignored local notes. Follow [run retention](artifact-storage.md#run-retention): preserve results,
logs, original screenshots/reports and one immutable APK per build; retire successful/superseded
guest disks and test databases promptly. Retain at most two failed guests only while their disks
help diagnosis. Core16 fixture cleanup and filesystem01 guest retirement have verified receipts.

Update this handoff with the current checkpoint and next action. Put detailed chronological
acceptance in the owning ticket so future workers need not reread superseded instructions.
