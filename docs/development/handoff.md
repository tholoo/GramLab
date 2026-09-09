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

Core19 passes all **1,192 non-Android tests at 88.11% coverage**. Static17 passes all **67 documented
commands**; the changed diagnostic scope also passes strict typing/Ruff, and configuration/links
validate in 265 Markdown files. Typed document World99, multipart100,
codec101, Bot API102, v5 client HTTP103 and atomic World creation13 are resolved. Standalone
media edits106 are integrated and verified at the World/HTTP boundary. The real-bot scenario105
is integrated; original Android acceptance remains pending. [Documents](documents.md) records
implemented forced-file behavior and standalone edits, including their limits.

Normal30 is built with complete ordered 30-patch source provenance and original document delivery.
Native03 retains the actual timeout archive:31 cases pass, one fails with AndroidUtilities
NoClassDefFoundError/ExceptionInInitializerError, and case33 waits in FilePathDatabase.getPath
through loadOrdinaryDocument. Seven watchdog samples show the same wait and no database queue
thread. This narrows diagnosis; it does not yet establish whether reduced fixture startup or
production caused the initialization failure. The source APK and deadlines remain unchanged.
Native02's timeout and failed archive, and native01's unavailable preflight skip, remain preserved.

The prior normal29 codec gate passes34 actual native cases; the same probe rejects normal28 for
its absent codec class. Earlier failed core/native results remain retained with their specific
corrections or unresolved causes. Do not infer an unrelated failure's cause from a later pass.

## Active work and next actions

1. [104: original document delivery](../../.scratch/rich-messages/issues/104-ordinary-document-native-delivery.md)
   is integrated with41 affected host checks, strict typing and Ruff passing. Bounded source
   reconstruction matches all29 prior patches and private staging verifies all five changed files.
   Normal30 is built. Instrumentation08 diagnostics are integrated with44 host checks and all33
   compile-input hashes verified. Actual native03 captures initialization/case records and bounded
   thread stacks successfully through app-owned tar/base64 retrieval. The worker is investigating
   the first AndroidUtilities initialization failure and subsequent database-queue wait. Preserve
   this red; expose the original cause and shorten the focused platform loop before changing
   production or increasing a deadline. Watchdog coverage starts at Instrumentation.onStart;
   earlier Application construction is outside that diagnostic coverage. Each run uses a fresh AVD.
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
5. [107: public runner v5](../../.scratch/rich-messages/issues/107-document-runner-v5.md) has22
   new and176 affected passing worker checks, but independent review found unsafe document row
   matching: any prefix with the expected caption could match. The worker is adding descriptor-bound
   type/size matching and zero-tap rejection controls at the dispatch boundary. That correction
   is now frozen with14 focused and42 affected worker checks passing; coordinator review and
   native execution remain pending. Keep default3 and
   explicit3/4 unchanged. Integration and public native acceptance remain gated on104 delivery.

[106: standalone media edits](../../.scratch/rich-messages/issues/106-standalone-media-edits.md)
is resolved for its bounded World/HTTP implementation after19 integrated cases and the combined
core/static gates. The empty-caption false-edit regression has eight actual red/green cases.
Coordinator checks independently specify complete cross-kind messages and use a valid oversized
PNG; an injected one-byte limit increase fails through real HTTP. [108: Android edit acceptance](../../.scratch/rich-messages/issues/108-native-standalone-media-edits.md)
is frozen on its worker branch with five focused host checks passing, extending the existing
real-bot/UI harness with four callback-driven
caption/cross-kind edits, retained D1 reuse, exact transfers and cold restart. Host implementation
is complete at the worker boundary; coordinator review/integration and native execution wait for104.

Remaining operational work includes default upload classification, albums, approved automatic
rich detection, wider rich-button placement/recovery and representative combined workflow/current-APK
regression. [Album source findings](albums-references.md) now use corrected pinned identities; group allocation,
request bounds and complete-group bridge application still need a frozen implementation contract. Preserve the full inventory; explicit unsupported errors do
not complete compatibility.

## Public-source preparation

[109: public collaboration](../../.scratch/rich-messages/issues/109-public-source-readiness.md)
adds a verified English-only README example, an original English glass screenshot and explicit
MIT/BSL/GPL source notices. No confirmed real credential was found in the tracked tree or reachable
history; the scanner's sole credential-pattern report is a public test correlation value. Historical
private consumer and machine notes were removed from both GitHub branches after explicit approval.
The atomic replacement rewrote 548 commits while preserving current source trees byte for byte.
GitHub remains private; visibility is a separate decision. This task does not close native readiness.

Local worker branches still retain their old ancestry and pending work. Before resuming or merging
one, migrate its reviewed changes onto the cleaned history and update its local assignment. Never
merge or push a legacy branch directly. The coordinator retains the old/new commit map and branch
inventory in ignored audit storage. Historical APK/test identifiers remain evidence of those runs;
the history rewrite does not change their recorded source or artifact bytes.

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
