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

Core18 passes all **1,183 non-Android tests at 88.11% coverage**. Static17 passes all **67 documented
commands** and configuration/links in 263 Markdown files. Typed document World99, multipart100,
codec101, Bot API102, v5 client HTTP103 and atomic World creation13 are resolved. Standalone
media edits106 are integrated and verified at the World/HTTP boundary. The real-bot scenario105
is integrated; original Android acceptance remains pending. [Documents](documents.md) records
implemented forced-file behavior and standalone edits, including their limits.

Normal30 is built with the complete ordered 30-patch source provenance and the original document
delivery implementation. Its first actual loader suite timed out inside instrumentation after
240 seconds, and archive retrieval failed. This establishes a failed acceptance run, not the
cause of the stall. The earlier preflight run selected the wrong APK environment variable and
skipped; it is recorded as unavailable coverage. Neither is a passing native document gate.

The prior normal29 codec gate passes34 actual native cases; the same probe rejects normal28 for
its absent codec class. Earlier failed core/native results remain retained with their specific
corrections or unresolved causes. Do not infer an unrelated failure's cause from a later pass.

## Active work and next actions

1. [104: original document delivery](../../.scratch/rich-messages/issues/104-ordinary-document-native-delivery.md)
   is integrated with41 affected host checks, strict typing and Ruff passing. Bounded source
   reconstruction matches all29 prior patches and private staging verifies all five changed files.
   Normal30 is built. Diagnose its actual240-second instrumentation timeout before changing
   production or increasing the deadline. The worker is adding bounded per-case progress/thread
   diagnostics and reliable app-owned archive retrieval; preserve the original failure even if
   evidence retention also fails. Review that fixture follow-up, use its immutable probe, then
   rerun the35-case original loader suite and cold restart on the existing APK.
2. The atomic publication primitive has separate actual target-process evidence: app external
   files are writable, Java/Os hard links fail with access denied, and a bounded no-replace rename
   succeeds for absent/Unicode paths and preserves occupied targets. Eight two-source races retain
   one complete winner and unchanged loser. Production uses the existing GPL JNI library and
   bounded UTF-8 syscall path. These primitive results do not establish complete loader delivery.
   Runtime evidence is limited to the pinned x86_64 guest. Target instrumentation suppresses
   Application.onCreate explicitly and verifies framework identity, zero accounts and isolation.
3. Preserve the corrected cache10 boundary: ordinary filename-only documents do not enable the
   original video preload stream. Above2MiB, reject locally through both loader entrypoints with
   zero requests/UI/files, then verify a normal retry. Keep original small-file behavior. The
   prepared native controls remain pending; a generic document preloader is not required here.
4. [105: real-bot document UI](../../.scratch/rich-messages/issues/105-ordinary-document-native-ui.md)
   has three passing integrated host cases covering the complete contained bot scenario, bounded
   failure evidence and full ordered APK input binding. Actual rows/captions/emoji/keyboard,
   download/callback actions, exact destination bytes, phase-local GETs, warm reuse and cold restart
   still require execution after104 passes.
5. [107: public runner v5](../../.scratch/rich-messages/issues/107-document-runner-v5.md) is frozen
   on its worker branch:22 new and176 affected host cases pass, with two retained baseline failures.
   Review is underway. Integration remains gated on104 native delivery; default3 and explicit3/4
   behavior must remain unchanged. Then exercise the public runner on Android with complete mixed
   document/photo/emoji/rich-button state.

[106: standalone media edits](../../.scratch/rich-messages/issues/106-standalone-media-edits.md)
is resolved for its bounded World/HTTP implementation after19 integrated cases and the combined
core/static gates. The empty-caption false-edit regression has eight actual red/green cases.
Coordinator checks independently specify complete cross-kind messages and use a valid oversized
PNG; an injected one-byte limit increase fails through real HTTP. Android edit acceptance remains
separate: reuse the existing real-bot/UI harness for caption edits and media replacements.

Remaining operational work includes default upload classification, albums, approved automatic
rich detection, wider rich-button placement/recovery and representative combined workflow/current-APK
regression. [Album source findings](albums-references.md) now use corrected pinned identities; group allocation,
request bounds and complete-group bridge application still need a frozen implementation contract. Preserve the full inventory; explicit unsupported errors do
not complete compatibility.

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
