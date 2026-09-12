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
was approved on 2026-09-12 as a deterministic offline GramLab emulation. The complete
[album contract](albums-implementation-proposal.md) was approved on 2026-09-12 with grouped edits
deferred and is now frozen.

## Accepted integration checkpoint

Core20 passes all **1,247 non-Android tests at 88.12% coverage** with no failures, errors or skips.
Static19 passes all **70 documented commands**, including the public document-v5, custom-emoji-v5
and residual-rich acceptance scopes that were absent from the previous recipe; configuration/links
validate in 278 Markdown files. Typed document World99, multipart100,
codec101, Bot API102, v5 client HTTP103 and atomic World creation13 are resolved. Standalone media
edits106, the real-bot scenario105 and the clean public runner-v5 migration107 are integrated.
[Documents](documents.md) records implemented forced-file behavior and standalone edits, including
their limits.

The current checkout collects exactly1,247 non-Android and68 Android cases with no overlap. Their
ordered manifests are retained as `artifacts/current-source-{non-android,android}-collection-01.json`.
A fresh approval-independent rich-target/clipboard/unrelated-edit/recovery host selection passes52/52 in14.533 seconds at
`artifacts/rich-button-current-host-01.xml`. Do not reuse the historical 53-case Android count for
the final gate.

Normal30 has complete ordered30-patch source provenance and unchanged APK SHA-256
`a964bbaccaaf59719d966a72ecd85de4288d146887e3f7ff7d50be7281df726b`. Document-delivery native08
passes35 original target-instrumentation cases plus a separate cold-process case. The original
LaunchActivity/media-edit native10 gate passes in118.862 seconds with eight inspected captures,
178 successful loopback requests, exactly one D1 GET, one P1 GET and one D2 GET, exact destination
bytes, callback-driven D1→P1→D2 edits and cold restart. No production patch or APK rebuild was
needed; the corrected acceptance harness decodes UIAutomator entities, pins document-only
auto-download settings, targets the original mdpi radial control, and closes client/proxy lifetimes
before their bridge endpoints.

The prior normal29 codec gate passes34 actual native cases; the same probe rejects normal28 for
its absent codec class. Earlier failed core/native results remain retained with their specific
corrections or unresolved causes. Do not infer an unrelated failure's cause from a later pass.

Public-runner document native06 passes the complete explicit-bridge5 CLI workflow in116.353 seconds
on the unchanged normal30 APK: the contained real bot uploads/downloads/reuses the forced document,
the original client renders it, accepts the inline callback and survives repeated launches, and the
scenario retains complete World/Bot API comparisons plus two inspected captures. Its adapter fixes
the observed no-space RTL filename descriptor, retries transient incomplete accessibility children,
and freezes tap receipts at `callback.created` despite a fast bot answer. The corrected affected
host gate passes43 cases; exact native transfer/cache bytes remain native08/native10 evidence.

The pre-existing public rich-target Android case now also passes1/1 on the unchanged normal30 APK
in103.950 seconds at `artifacts/rich-button-normal30-baseline-01.xml`. All six retained original
frames were inspected: row/inline callback, copy and disabled states remain visible with mixed
English/Persian labels; both clipboard confirmations and unrelated-message stability are present.
The run-local APK matched the canonical normal30 hash and was removed after the evidence was packed;
the JUnit, report, observations, journals and frames remain.

Residual rich-button native acceptance also passes1/1 in89.464 seconds at
`artifacts/rich-button-residual-normal30-native-04.xml`. The original observer rejects the partly
visible target at exact bounds `[22,-9,302,25]` before input, while explicit RTL content, callback,
copy and nested controls remain operative in upstream payload order. A real process restart
invalidates the old target and a fresh observation succeeds; a deliberately lost terminal reply is
recovered without a second touch. Exactly three original taps, semantic/API correlation, clipboard,
API36, zero accounts and containment pass. [Ticket115](../../.scratch/rich-messages/issues/115-rich-button-residual-native-acceptance.md)
is resolved without a renderer patch.

Custom emoji's public bridge5 case passes1/1 in81.195 seconds at
`artifacts/custom-emoji-normal30-native-04.xml`; the existing current-APK codec gate also passes.
The fresh focused fault gate passes1/1 in281.715 seconds at
`artifacts/custom-emoji-normal30-fault-03.xml`, including exact failed/idle pixels, all recovery
phases, shared transfer/cache behavior and inspected captures without platform-report interference.
The clean lifecycle timing run has exact authored pixels and lockstep carrier states across all24
captures. The approved bounded-window oracle selects captures2–23 for every carrier, proving22 exact
frames across6.84 seconds while retaining whole-sequence state-order checks. Its32-case focused
suite, strict typing and Ruff checks pass; tickets120 and116 are resolved without another guest run.

The approved offline rich detector and Android patch0031 are integrated. The merged focused gate
passes183 scanner/Bot-API cases; all15 patch-stage cases, strict typing and Ruff pass. The worker's
exact full pre-integration gate passed1,401/1,401 at88.25% coverage. Ticket119 remains claimed only
until patch0031 is compiled into the album-era APK and its collected original codec case passes.

## Active work and next actions

1. [104: original document delivery](../../.scratch/rich-messages/issues/104-ordinary-document-native-delivery.md)
   and [105: real-bot document UI](../../.scratch/rich-messages/issues/105-ordinary-document-native-ui.md)
   are resolved on normal30. Preserve the verified cache10 boundary: filename-only ordinary
   documents above2MiB reject locally without a generic preload stream; the complete35-case suite,
   persisted destinations, cold-cache reuse, zero accounts and loopback-only containment pass.
2. [108: Android standalone edits](../../.scratch/rich-messages/issues/108-native-standalone-media-edits.md)
   is resolved by native10. D1 and D2 are tap-driven while stock photo auto-download remains on;
   trace keys are `-1_-1.pdf` and `-1_-2.pdf`, while the atomically published presentation files
   live under Telegram Files. P1 is removed when D2 replaces it. Original screenshots, XML,
   complete World/Bot API state and the report remain under
   `artifacts/native-media-edit-android-10/`.
3. [107: public runner v5](../../.scratch/rich-messages/issues/107-document-runner-v5.md) is resolved.
   Preserve default3 and explicit3/4 while bridge5 carries ordinary documents; keep exact
   descriptor/ambiguity rejection and creation-time native callback receipts.
4. Continue the operational milestone with albums. The approved
   [classification contract](default-document-classification-proposal.md) is integrated: general
   files remain documents and recognized unsupported specialized families reject atomically.
   [Ticket110](../../.scratch/rich-messages/issues/110-default-document-classification.md) passes73
   affected HTTP/edit/contained-bot cases; album-core ticket112 is now assigned.
5. The [album contract](albums-implementation-proposal.md) is frozen with its 100,000,000-byte
   logical aggregate, rollback-safe World-wide group IDs, bridge-v6 complete-group pagination and
   grouped edits deferred. [Ticket111](../../.scratch/rich-messages/issues/111-album-contract.md) is
   resolved. Tickets112–114 are specified in dependency order; ticket112 starts after serialized
   completion of ticket110. The approved automatic rich detector's host behavior and patch0031 are
   integrated in [ticket119](../../.scratch/rich-messages/issues/119-rich-auto-detection-implementation.md);
   its original codec gate awaits the album-era APK.
6. Approval-independent acceptance work is split into
   [115: residual rich-button native acceptance](../../.scratch/rich-messages/issues/115-rich-button-residual-native-acceptance.md),
   [116: current-APK public custom emoji](../../.scratch/rich-messages/issues/116-custom-emoji-current-apk-public-runner.md),
   and [118: reproducible setup docs](../../.scratch/rich-messages/issues/118-current-reproducible-setup-docs.md).
   Tickets115 and118 are resolved: residual rich input/restart/recovery passes on normal30, and the
   public example, Android source/build boundaries and complete 30-patch
   queue are current without publishing or embedding an APK. The documented echo command also
   passes with explicit bridge5 in a fresh loopback-only namespace at
   `artifacts/setup-echo-v5-01/`. Ticket116 is resolved: its public, codec and fault surfaces pass on
   normal30, and [ticket120](../../.scratch/rich-messages/issues/120-custom-emoji-bounded-timing.md)
   resolves the approved bounded timing replay. Every Android guest
   remains serialized. The
   final composed workflow is
   [117](../../.scratch/rich-messages/issues/117-final-representative-workflow.md) and cannot close
   before the approved fidelity implementations and album work.

Remaining operational work includes albums, approved automatic rich detection and the combined
current-APK regression.
Preserve the full inventory; explicit unsupported errors do not complete compatibility.

## Public-source preparation

[109: public collaboration](../../.scratch/rich-messages/issues/109-public-source-readiness.md)
adds a verified English-only README example, an original English glass screenshot and explicit
MIT/BSL/GPL source notices. No confirmed real credential was found in the tracked tree or reachable
history; the scanner's sole credential-pattern report is a public test correlation value. Historical
private consumer and machine notes were removed from both GitHub branches after explicit approval.
The atomic replacement rewrote 548 commits while preserving current source trees byte for byte.
GitHub remains private; visibility is a separate decision. This task does not close native readiness.

A current-source re-audit after the document, rich-button, setup and custom-emoji integrations
scanned696 tracked blobs. No private key, provider token, JWT, credential URL, targeted consumer
reference, user-home path or recorded local proxy matched; nine generic credential assignments are
the existing synthetic test fixtures. Gitleaks8.30.1 reports zero findings across every commit since
the cleaned-history checkpoint. Ignored runtime artifacts and legacy local worker refs remain
outside this publication claim.

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
The current audit permanently removed 20 earlier hash-matched custom-emoji run-local APK copies
totaling2,779,159,640 bytes while retaining both canonical APKs and all
JSON/XML/screenshots/reports. Current normal30 custom-emoji acceptance later retired48 guest disks
and9 matching APK copies, reclaiming9,478,701,056 allocated bytes; residual rich acceptance retired
four guest disks and four matching copies, reclaiming4,993,269,760 bytes. One custom-emoji timing-
failure guest was retained through diagnosis, then its final six AVD images were retired after234
evidence files were revalidated, reclaiming another951,885,824 bytes. No guest disk from current
normal30 custom-emoji or residual-rich acceptance remains. Four
older custom-emoji core basetemps totaling about 618 MiB remain because deleting their copied test
trees requires a separate explicit retention decision; their top-level JUnit/logs are already
retained independently.

The three recent clean worker checkouts for current setup docs, public custom-emoji v5 and residual
rich buttons were also retired after their branch tips were proven ancestors of the integration
head and no process used their paths. Their branches remain. Before removal, the coordinator copied
and byte-verified the required red/green artifacts:289 regular public custom-emoji files, its two
JUnits and all three residual-rich JUnits. The ignored receipt is
`.cache/local-notes/integrated-worker-worktree-retirement-01.json`. Historical worktrees were not
bulk-deleted; their independent evidence and legacy-history restrictions still require individual
review.

Three additional clean migrated-history worktrees—document runner v5, native media-edit acceptance
and document-delivery fixture initialization—were then retired under the same checks. Their branch
tips remain ancestors of the integration head. The only unique ignored evidence was the document-
runner migration: all four ticket-referenced JUnits and its111-file final work tree were copied and
byte-verified in the coordinator artifacts before removal. The other two contained dependency
caches only. The ignored receipt is
`.cache/local-notes/migrated-worker-worktree-retirement-01.json`.

Update this handoff with the current checkpoint and next action. Put detailed chronological
acceptance in the owning ticket so future workers need not reread superseded instructions.
