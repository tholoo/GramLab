# Next-agent handoff

## Interactive Android playground checkpoint

The playground startup follow-up runs declared bots and semantic setup concurrently with the clean
Android boot, waits only for explicitly selected bots to reach polling, then attaches native input
and renders the final setup capture once. Same-persona native navigation keeps the running client
process, and the emulator now uses four bounded virtual cores. A downstream real-client acceptance
reached its live control boundary in 47.8 seconds rather than roughly 149 seconds while preserving
all seeded chats and menus. Snapshot caching was rejected after the pinned software-rendered
emulator failed strict reload tests; no unstable cache path remains.

Programmatic-scenarios ticket 12 adds `interactive-android` to the public runner and persistent
playground. The original Telegram client still runs in an isolated headless emulator; a separately
contained scrcpy component exposes that guest screen as a normal clickable desktop window. The
outer supervisor receives one explicit host X11 socket, and the viewer receives only its fixed
private remount. Focused tests reject non-socket paths and prove neighboring display sockets and
ambient host paths remain hidden. The interactive profile requires its pinned scrcpy executable.

The final serialized downstream acceptance opened the visible Telegram client, sent a command
through the native composer, observed the real consumer response, reset to the exact seeded World,
and stopped with a passing result. Setup independently exercised an original rendered rich-button
callback. Guest IPv4 and IPv6 remained blocked. Direct pointer/keyboard interaction is supported;
native Telegram member-picker administration is not, and `add-bot` remains an explicitly described
authenticated World transition. Publication remains subject to explicit remote approval.

The final contained core gate passes 1,632 tests at 85.65% coverage. Repository-wide Ruff lint and
format checking, strict typing for every changed source and newly typed test scope, focused Android
profile/runner tests, and direct Nix formatting/evaluation checks pass. Building the declared Nix
checks was not completed because the pinned revision's tool closures were not present locally and
offline realization attempted upstream downloads.

## Earlier persistent playground checkpoint

Programmatic-scenarios ticket 10 adds a consumer-neutral persistent playground over the public
runner. A finite setup scenario establishes the baseline, then real bot processes remain available
through authenticated Unix-socket `status`, `send`, `tap`, `capture`, `add-bot`, `reset` and `stop`
commands.
Reset terminates consumer namespaces, restores owned World and bot directories, preserves the run
identity and refreshes the active Android chat. The public simulation acceptance proves a real
consumer message and rich callback/edit, creator-authorized bot addition with an ordinary
`my_chat_member` delivery and reply, exact visible-World reset, removal of consumer file mutations,
and denial of a detached old-process write. It repeats bot addition after reset, rejects a member
actor and a tampered capability without stopping the owner, and proves idempotent stop.

The Android path reuses the existing headless original client, composer, rich-button input and
blocked guest egress boundary. The earlier serialized acceptance passed against patch-35 APK SHA-256
`fff0c33f6991202b08a63e77a501f3bc188eecda9ae45047bf1cf39400c11521`: addition and reset were
rendered and captured as PNGs, and guest IPv4/IPv6 remained blocked. The final contained
non-Android gate passed all 1,625 tests at 85.11% coverage; JUnit SHA-256:
`0e2043f13346026605dc861daffa17497f88e383548f1d86822caa3a7920618c`. Repository Ruff lint,
formatting and maintained strict typing scopes pass. Publication remains subject to explicit remote
approval.

## Group rich-input checkpoint

Programmatic-scenarios ticket 09 adds generic explicit-member rich-button input for supergroups and
permits a member's first composer message without weakening the private Start Bot invariant. The
public Android group scenario passes one original rendered-button tap with callback actor `3` and
chat `-1`, bot edit/restart, original-composer send, exact history and three inspected screenshots.
Patch 0035 changes only `GramLabButtonObserver`, stages exactly against patch 0034 and builds offline.
The local APK SHA-256 is
`fff0c33f6991202b08a63e77a501f3bc188eecda9ae45047bf1cf39400c11521`; the retained passing result
under `artifacts/group-rich-native-05/` has SHA-256
`910176a564bbdbdda4ae09b5cabb006b612ca2d156ebb94f3ffc542246bdb3ab`.

The complete contained non-Android gate passes all 1,623 tests in 119.62s at 89% coverage with zero
failures or skips. The JUnit SHA-256 is
`19ce0aef52550ac08d989eb0580b66cc8f109fa043815e1cb1d958afed6f718d`; maintained strict typing,
repository Ruff lint and repository Ruff formatting checks also pass. Publication remains subject
to explicit remote approval.

## Earlier synthetic group checkpoint

Programmatic-scenarios tickets 07 and 08 now provide synthetic supergroups through the World,
local Bot API, schema-1 control service, typed scenario SDK, contained runner and original Android
client. Bridge v6 preserves the durable negative World group ID while the authenticated adapter
uses a non-colliding native channel ID, complete users/chat/history objects and explicit writable
permissions. Existing private-chat envelopes and their native path remain unchanged.

The public group example now performs a real member callback, bot edit, original-composer send,
bot restart, reply and cold client relaunch. The retained final run under
`artifacts/group-android-native-11/` passes exact four-message history, zero accounts and blocked
guest egress; all three original screenshots were inspected and show no false admin/Owner label.
The final APK SHA-256 is
`432168246376d98c3bd4eaebb791771401023946a5ef2c3f8f0c55291209c92f` and the Android profile
SHA-256 is `fe878c649232bd571a1a64f075a79c11f5db19d30b6e3b04c9573307da83c68f`.
Patch 0034 stages exactly three adapter/probe Java files without fuzz or offsets and builds
offline. The complete non-Android gate passes 1,619 tests at 88.83% coverage; focused group,
private-bridge, native codec, Ruff and strict typing checks also pass. Ticket 08 contains the
red-first chronology and exact artifact identifiers.

Next action: after explicit remote-publication approval, publish the task branch for integration.
The next product choice can then be made from the still-unsupported admin transitions, channels,
topics, multiple simultaneous clients, HTML parse modes, grouped-media edits or Mini Apps; native
group support does not silently broaden any of those boundaries.

## Objective and authorization

GramLab runs real local bots against one SQLite World and uses the actual Telegram Android
renderer. The isolated bot → Android → tap → callback → bot edit → restart loop is proven.
Simulation and Android share semantic state; only Android supplies rendering/input evidence.

The full [product inventory](../product/requirements.md) remains the goal. The
[first operational milestone](operational-milestone.md), covering messages/buttons, rich content,
photos/files/albums and custom emoji in one representative workflow, is now resolved at its
approved fidelity boundary. Mini Apps were deferred from that milestone only. The persistent
playground and live original-client window are implemented; native administration flows and
broader API/recovery/reporting remain unfinished.

The user approved the Android foundation and all four media/custom-emoji/mention/rich-button
designs, and resumed implementation. Follow [ADR0005](../adr/0005-local-media-and-client-interaction-boundaries.md)
and their frozen contracts. Local worker branches, coordinator merges and commits are authorized.
Keep runtime offline, use synthetic identities and zero real accounts, and preserve upstream
rendering. Consequential design, fidelity, licensing, runtime network and publication changes
still require consultation. The [automatic rich-detection policy](rich-auto-detection-proposal.md)
was approved on 2026-09-12 as a deterministic offline GramLab emulation. The complete
[album contract](albums-implementation-proposal.md) was approved on 2026-09-12 with grouped edits
deferred and is now frozen.

## Current completion checkpoint

Generic consumer compatibility now supports independent bot environments through trusted per-bot
profiles. `sendRichMessage` accepts `disable_notification`; URL and chosen-chat rich buttons
survive World/API/bridge/native projection; and generated rich entities retain required metadata.
Android runs select light or dark explicitly, detect a vanished client while waiting for UI, and
retain a bounded MP4 plus crash-oriented logcat on failure. Patch
`0033-rich-navigation-buttons.patch` stages against the pinned source without fuzz, and its rebuilt
APK passed an offline external-consumer validation in both themes. Consumer-runtime-profiles ticket
02 contains the focused generic contract and evidence. The capability set is verified for main
integration.

The consumer runner now accepts trusted per-bot runtime-profile overrides through
`--bot-profile ALIAS=PROFILE` and the equivalent Python mapping. A real contained bot imports a
dependency absent from GramLab's default profile, exchanges an update through the local Bot API,
and passes. A two-bot Python-runner case verifies that each component sees only its selected
profile closure even though the outer supervisor mounts their union for nested setup. Unknown
aliases and repeated bindings reject before output creation; results retain only SHA-256 profile
fingerprints. Focused runner cases, scoped Ruff and package strict typing pass. Android was not
required because component selection does not change the Android profile, adapter or rendering.
The final serialized non-Android gate passes all 1,608 tests at 88.96% coverage. The former
current-inline fixture mismatch is resolved by explicitly selecting bridge v4 for its custom-emoji
interaction while the public default remains v3. Consumer-runtime-profiles ticket 01 contains the
red/green record.

The Python-only [0.1.0a1 prerelease](https://pypi.org/project/gramlab/0.1.0a1/) is published from
tag `v0.1.0a1` at commit `2d0ec88e806fba189ef420f0745c74b464255e85`. It retains the tested
Python 3.13 and Pillow 12.3.0 constraints. GitHub Actions run
[34718534527](https://github.com/tholoo/GramLab/actions/runs/34718534527) passed separate build and
OIDC publication jobs without a stored PyPI token. Action pins, workflow syntax, lock, metadata
rendering, absolute README links, isolated wheel/sdist installs, CLI entry point, package contents
and all MIT/Boost notices passed release-specific checks. PyPI's two non-yanked artifacts match
the locally audited sizes and SHA-256 hashes; a fresh index install imports the typed API and runs
the CLI. The matching [GitHub prerelease](https://github.com/tholoo/GramLab/releases/tag/v0.1.0a1)
is live. The 45-entry archives contain no Android, tests, cache, Git or runtime artifacts. Do not
rebuild, replace or move this published version; Python-release ticket 01 records exact evidence.

Recommendation 1 from the developer-excellence report is implemented on `task/scenario-flows`:
installed and runner-contained scenarios can import `Scenario` plus typed `User`, `Bot`,
`Conversation`, `Message`, inline-action, callback, capture and interaction handles directly from
`gramlab`. The handles bind run identity, own common operations and expose immutable observations
with copied raw results. Bounded conversation, callback and bot-state waits repeat reads only, so
uncertain input operations are never retried. All twenty raw operations and the schema-1 wire
contract remain available unchanged. The echo and inline examples now demonstrate the public flow;
no network, fidelity, Android, licensing or publication boundary changed.

The nine-case real-loopback flow collection, the affected control/client/runner collection, both
contained echo scenarios and the contained inline callback scenario pass. Strict typing for the
changed package and examples, scoped Ruff lint/format, diff validation and offline wheel/sdist
inspection pass; the wheel imports the new root exports. A full non-Android run reached 88.70%
coverage with 1,587 passes and four failures: the known default-v3/custom-emoji-v4 baseline plus
three fixture/example compatibility failures introduced by the migration. Those three exact tests
pass after focused fixes; at the user's direction the whole gate was not repeated. Android was not
rerun for this additive scenario-authoring layer. Programmatic-scenarios ticket 06 contains the
contract and evidence; ticket 02 remains open for the wider runner workflow.

The three Strong architecture-review candidates are implemented on
`task/deepen-world-and-bridge` as separate commits: `1da28fd` deepens final message publication,
`266d804` owns complete media-group topology and delivery slicing, and `7d169f2` centralizes client
bridge version policy and complete semantic envelopes. World keeps the existing client façades;
the HTTP adapter no longer reads World private implementation. `CONTEXT.md` now defines message
publication, media group and client bridge schema. No persisted/public schema, fidelity target,
network, licensing or grouped-edit decision changed, and Android was not rerun.

Focused publication, topology, World and HTTP bridge checks pass, including a new 24-case public
version matrix. Scoped Ruff lint/format and strict mypy pass. The clean-shell complete non-Android
gate passes 1,581 tests at 88.61% coverage with one baseline failure: the unchanged current-inline
CLI test uses default bridge v3 but expects a custom-emoji callback requiring v4. The same isolated
test fails at pre-branch `f1a5200`; architecture-deepening issue 02 records the required maintainer
choice without changing the preserved default. Full Ruff lint passes; full format checking reports
only an unchanged pre-branch layout in `tests/test_media_group_runner_v6.py`.

Commit `5cbe830` adds the public bridge-v6
[representative workflow](representative-workflow.md). The same real local bot/scenario passes in
simulation and in the original normal31 Android renderer. It composes bilingual ordinary text,
automatic and explicit rich entities, ordinary and rich callbacks, edits, exact callback replay
across bot restart, PNG/JPEG upload and reuse, default and forced documents, true photo/document
albums, and static/animated custom emoji. Mini Apps remain deferred.

The retained runner result under `artifacts/representative-android-03/` passes in 148.200 seconds
with 17 final messages and five inspected original captures. It uses the immutable normal31 APK
SHA-256 `e60a873fc0283b270a35538c63a5f6e701e74cfecb8f10cfce35af670c57be7a`, API36 x86_64,
bridge6, seed117 and frozen time. World, Bot API, bridge and native input comparisons are complete;
the guest has zero accounts, loopback-only networking and the required filesystem separation.

The enclosing JUnit records a failure after the successful runner because the first test helper
restored a redacted accessibility field at only one of two valid nesting locations. The corrected
helper replayed every assertion over the retained result successfully. The emulator was not rerun
again at the user's direction. The prior complete host gate passes 1,508/1,508; the new simulation,
17 affected rich tests and scoped static checks pass. Current collection is 1,553 non-Android and
74 Android tests. The normal31 73-case diagnostic, exact five-case retry and final album-only retry
provide transparent case-level union evidence, not a clean aggregate rerun.

Tickets113,114,117 and119 are resolved for this milestone. Remaining product work includes Mini
Apps, HTML parse modes, grouped-media edits, external Telegram conformance, production emoji
entitlement and interactive Android mode.

## Earlier integration detail

Core20 passes all **1,247 non-Android tests at 88.12% coverage** with no failures, errors or skips.
Static19 passes all **70 documented commands**, including the public document-v5, custom-emoji-v5
and residual-rich acceptance scopes that were absent from the previous recipe; configuration/links
validate in 278 Markdown files. Typed document World99, multipart100,
codec101, Bot API102, v5 client HTTP103 and atomic World creation13 are resolved. Standalone media
edits106, the real-bot scenario105 and the clean public runner-v5 migration107 are integrated.
[Documents](documents.md) records implemented forced-file behavior and standalone edits, including
their limits.

That earlier checkpoint collected exactly1,247 non-Android and68 Android cases with no overlap. Its
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

The approved offline rich detector and Android patch0031 were integrated. The merged focused gate
passes183 scanner/Bot-API cases; all15 patch-stage cases, strict typing and Ruff pass. The worker's
exact full pre-integration gate passed1,401/1,401 at88.25% coverage. At this checkpoint, ticket119
remained claimed until patch0031 could be compiled into the album-era APK and its codec case run.

Atomic photo/document albums are integrated through the host and bridge boundaries. Schema10,
strict homogeneous 2–10-member `sendMediaGroup`, rollback-safe World-wide group IDs and bridge-v6
complete-group pagination pass53 focused coordinator cases. The combined loopback-only
non-Android gate passes1,508/1,508 at88.19% coverage. At this checkpoint ticket112 was resolved;
ticket113 owned the GPL Android adapter patch and ticket114 the later native/public acceptance.

## Superseded work split

The numbered split below records how this milestone was assembled. Its pending descriptions are
historical; the current completion checkpoint above supersedes them.

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
   affected HTTP/edit/contained-bot cases.
5. The [album contract](albums-implementation-proposal.md) is frozen with its 100,000,000-byte
   logical aggregate, rollback-safe World-wide group IDs, bridge-v6 complete-group pagination and
   grouped edits deferred. [Ticket111](../../.scratch/rich-messages/issues/111-album-contract.md) is
   resolved, and ticket112's host/bridge implementation is integrated. Ticket113 now owns the
   Android adapter; ticket114 follows for native/public acceptance. The approved automatic rich
   detector's host behavior and patch0031 are integrated in
   [ticket119](../../.scratch/rich-messages/issues/119-rich-auto-detection-implementation.md); its
   original codec gate awaits the same album-era APK.
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
   final composed workflow was scheduled as
   [117](../../.scratch/rich-messages/issues/117-final-representative-workflow.md) after the approved
   fidelity implementations and album work.

Original-Android album delivery and the rich auto-detection codec gate described above are now
complete. No clean combined 74-case rerun is claimed: preserve the retained diagnostic and narrow
rerun record. Explicit unsupported errors still do not complete the wider product inventory.

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
