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

Core16 passes all **1,126 non-Android tests at 88.02% coverage**. Static15 passes all **64 documented
commands** and configuration/links in259 Markdown files. The later handoff-only reorganization
gets its own document validation. This includes typed document World99, multipart100, codec101
host checks, Bot API102, v5 client HTTP103 and atomic World creation13; these bounded tickets are
resolved. [Documents](documents.md) records the implemented forced-file HTTP profile and limits.

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
   in its assigned worktree. A separate read-only reviewer is checking the draft. Preserve distinct
   document/emoji identities, exact v5 dependencies, rejected-response atomicity, original
   destinations, cancellation, cache and notifications. Review found same-world authority rotation,
   cache10 lifecycle and missing v4/v5 native controls; the worker is addressing them.
2. Resolve publication on the actual external-files filesystem before building. Filesystem01 on
   unchanged normal29 reaches loaded native code with zero accounts and no HTTP requests, but
   fails with SecurityException inside external_files_primitives. Its current recorder lacks the
   failing stage/cause; the worker is preparing bounded diagnostics. This is not evidence for or
   against hard-link support. Original failure evidence remains; its terminal guest disks are retired.
3. Cache10 above2MiB needs the original partial-preload lifecycle and subsequent full-load upgrade.
   The worker may provide explicit local rejection as an interim checkpoint while preserving small
   file behavior. That does **not** close104 or reduce the required final cache behavior. Review the
   proposed original-loader data-source seam/transport needs before consequential changes.
4. Review [105: real-bot document UI](../../.scratch/rich-messages/issues/105-ordinary-document-native-ui.md)
   independently. Its worker reports one contained simulation pass with complete bot API/state
   comparisons; coordinator review and native execution remain. Freeze the owned harness against
   the reviewed104 trace/route contract. Root owns the APK build and actual UI/loader acceptance.
5. Merge only reviewed frozen branch tips, run affected checks, and build using the existing
   incremental cache. Enable the host's explicit v5 selector only after delivery is verified.
   Capture original rows/captions/emoji/keyboard, real download/callback actions, exact destination
   bytes, phase-local GETs, warm reuse, cold restart and complete matching World/API state.

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
