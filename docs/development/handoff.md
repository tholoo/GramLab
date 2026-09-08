# Next-agent handoff

## Current state and objective

GramLab runs a real local bot against a SQLite World and renders its messages in the actual
Telegram Android application. The bounded bot → Android → inline tap → callback → bot edit →
restart/recovery loop is proven. Simulation and headless Android share semantic state; only Android
provides rendering/input evidence. Interactive mode remains unfinished.

The full [product inventory](../product/requirements.md) remains the objective: broader versioned
Bot API coverage, concurrent programmable scenarios, recovery/faults, multilingual rich messages,
media/custom emoji/Mini Apps, previews, performance diagnostics and reports. The first loop is a
checkpoint, not completion. Consult the [compatibility matrix](../compatibility/matrix.md) before
claiming any feature; explicit unsupported behavior remains part of the contract.

The user clarified the [first operational milestone](operational-milestone.md): messages/buttons,
rich messages, photos/files and custom emoji are required. Mini Apps may follow later and remain
in the full goal. A text-only subset is not the operational milestone.

## Latest integration checkpoint

The full operational milestone remains incomplete. Earlier failures remain retained and are not
superseded by a later pass unless the specific correction is demonstrated.

The user requested disk cleanup. Old guest disks, archives and reproducible caches were removed. Follow [run retention](artifact-storage.md#run-retention): save review
artifacts, remove successful guest disks immediately, and retain at most two failed guests only
while their disks help diagnosis. Historical disk paths may be absent; screenshots, logs, native
JSON, APKs and provenance remain. Exact paths and cleanup receipts stay in ignored local notes.

- Normal26 passes 25 actual native-buffer/SQLite provenance cases. Normal27 preserves original
  drawing/input and normalizes observer coordinates; seven real Android Canvas/Matrix cases now
  pass, including a verified first-corner overflow. The original projective fixture red remains.
- Normal27's public native test passes without tracing in 106.49 seconds: all six visible row/
  inline callback, copy and disabled controls succeed; hidden/offscreen reject before dispatch;
  repeated receipts remain unchanged. Passive12 also passes in 151.69 seconds. The owned-popup
  correction has 108 focused host/simulation checks and actual native acceptance. Earlier
  native10/11 readiness failures remain incompletely diagnosed; source review finds arm ACKs can
  reference old draws. Fresh startup-instrumented native15 accepts88's complete visible/ABA histories, events, API
  ordering, receipts and native provenance in 81.47 seconds. Actual clipboard paste and native
  unrelated-edit survival remain open under74/92. Do not infer those from the current receipt-status test.
- Fresh original custom-emoji UI09 passes in 130.06 seconds on unchanged normal24: initial static
  rendering, real bot callback/edit, original settings, three animated carriers and unchanged
  cold-cache restart. All 24 conservative acquisition bounds are 140–210 ms (median 160 ms).
  The unchanged spatial/phase oracle accepts all 72 carrier frames; independent PNG decoding
  exactly matches every retained raw frame. Original captures and desktop/mobile reports are
  inspected. Ticket86 has 79 combined capture/oracle checks; no renderer or fixture was changed.
- Ticket66's fresh full normal24 fault regression passes in 195.89 seconds after89's progressive
  fixture/transparent forwarding correction and90's diagnostic integration. All three document
  failure/recovery cases and original shared-transfer assertions pass, including full isolation
  and zero accounts. The focused shared gate separately passes in 66.59 seconds. Original
  captures are inspected and reports retained; successful and obsolete failed guest disks are
  retired. Earlier reds remain: measured proxy timeout in native02 and UI reopen failure before
  the shared case in native03. The latter's intermittent cause remains unproven.
- Ticket69's fresh native mixed-content run passes in 84.80 seconds after correcting the expected
  callback-event shape. Complete six-message history, callback creation/answer and composer-send
  comparisons pass; the original capture and desktop/mobile report were inspected. The first red
  remains retained and successful guest disks were retired. Ticket88 expands native button state
  acceptance independently and now passes fresh native15. Native14
  failed the existing boot deadline before scenario execution and remains retained; actual clipboard paste and native unrelated-edit survival remain
  separate gaps. Unrelated message revisions do not bypass native geometry/freshness checks.
- Immutable APK storage has 20 integrated filesystem checks. Private Android patch staging is
  integrated with 15 passing checks, including all-new patches and bounded descendant-held
  output cleanup; contributor/CI checks include it. It never mutates the live source tree.

The current core11 checkpoint passes 968 tests at 87.36% coverage in 139.41 seconds with four
isolated workers and no simultaneous guest. All 57 documented static commands, Ruff lint/format
across 494 files and configuration/links in 243 Markdown documents pass. This includes92's failure
diagnostic,94 multipart metadata,95's corrected independent acceptance and96's schema-8 migration.
The gate exposed unclosed fixture database connections; explicit closure subsequently passes all
23 migration/media World checks with resource and unraisable warnings treated as errors. The
production migration is unchanged. Core08's earlier six recovery-fixture failures and correction
remain recorded; no production timeout, rendering or recovery behavior was changed to pass them.

Document research91 establishes pinned upload filename/MIME derivation and empty-file rejection.
Multipart metadata94 is resolved, preserving filename/type and exact image bytes. Storage96 is
resolved: schema 8 shares immutable bytes while preserving existing photo/emoji identities, grants,
callbacks and v3/v4 results. Its 53 affected World/migration/HTTP/bridge/real-bot checks pass together,
with authentic populated schema-7 fixture provenance. General documents and albums remain unsupported;
the next file implementation still needs typed document metadata/identity/grants and negotiated
client delivery, rather than treating this migration as file support.

Clipboard92's XML correction passes actual row-copy paste/clear in native02. Diagnostic native03
also passes inline-copy and inline-disabled paste/clear with complete unchanged semantic snapshots.
It still fails full acceptance: the row-disabled operation reads a draw sample 10,236 ms old and
rejects at the unchanged five-second guard before dispatch. Exact source hash, failure frame and
staged bootstrap are verified. Earlier native02's exact guard was not retained. The four-phase
rewrite is integrated with 26 focused checks: deliberate public observation per phase, same-lifetime
copy baseline for each disabled action, and terminal paste/clear; no expired-target renewal or input
retry. Native04 passes row-copy but rejects the next phase's inline-copy during preparation. Its
original observation and before-input PNG are retained, but no freshness-failure record exists;
the precise later preparation guard remains unproven and a bounded diagnostic follow-up is active.
The 968-test checkpoint predates this phase rewrite. The complete88 native gate remains separate
and unchanged. Diagnosed clipboard guest disks are
retired; their XML, screenshots, operation records, logs and source evidence remain.

Unrelated-edit95 is integrated with two focused controls and complete bot/native oracles. Native01
fails startup before actors. Startup-instrumented native02 boots and visibly applies the unrelated
edit, but rejects the target before input; its retained armed effect is already 4,978 ms after the
last drawn sample. The exact failing guard is not retained, so do not label its cause proven.
The scenario then waits for a callback that cannot arrive. A bounded follow-up removes redundant
preparation work, uses the original operation screenshot, and retains failures promptly. Native
unrelated-edit survival remains unproven. Startup collector processes/threads are terminal.

Exact run paths, cleanup identities and current process handles stay in ignored coordinator notes.
Successful core fixtures are retired immediately after preserving JUnit, logs and outcomes.
Ticket93 provides the [concrete offline rich auto-detection proposal](rich-auto-detection-proposal.md)
for user consultation; changing
the fidelity target remains unapproved and implementation must not start on that assumption.
Native unrelated-edit survival and the wider operational inventory remain required. Exact local
paths, process handles, cleanup receipts and active worker state stay in ignored coordinator notes.

## First action

Read [AGENTS.md](../../AGENTS.md) and the assigned ticket. Follow its linked testing, architecture,
offline safety, licensing and completion requirements before the corresponding action.

- The user approved all four designs on 2026-09-07 and explicitly resumed the goal. Proceed with
  [media](rich-photo-proposal.md), [custom emoji](custom-emoji-proposal.md),
  [mentions](rich-mention-proposal.md) and [rich-button targeting](rich-button-targeting-proposal.md)
  under [ADR 0005](../adr/0005-local-media-and-client-interaction-boundaries.md). Do not ask for
  these approvals again. Their implementations and acceptance gates remain incomplete.
  Shared immutable media/API/delivery is the first dependency. Coordinate the successor bridge
  schema before splitting core, GPL and real-bot acceptance work. Existing PNG/JPEG/WebP/WebM
  fixtures are prepared; fixture decoding does not establish runtime media support.
- [Local photos](photos.md) implement PNG/JPEG upload, bot-scoped reuse/download, immutable
  assets/grants and v3 revisions/dependencies under the frozen [media contract](media-implementation-contract.md).
  The pre-emoji combined core gate passed 510 tests at 81.98% coverage in 70.90 seconds. Native
  serialization/required-field corrections pass all 28 photo codec cases on normal22; normal23
  passes all four controlled response faults and explicit cold-restart recovery, with eight
  original captures inspected. The first-photo zero-tag correction is in patch 0021.
- Normal23 now passes original cancel/retry, shared-consumer loading and ordinary-edit global
  cleanup in 99.43 seconds, with nine inspected captures. A canceled shared cell receives the
  file completion notification without a bitmap; replacing an ordinary photo globally cancels
  the old transfer and leaves the unchanged shared cell's loading control. Preserve both
  original behaviors. [Ticket 49](../../.scratch/rich-messages/issues/49-media-native-interactions.md)
  records the original failed assumptions and corrected acceptance.
- The stronger rich-photo scenario passes in 105.85 seconds: an unchanged leading photo avoids
  whole-message cleanup while a second photo is edited; the new JPEG binds before the old shared
  PNG completes in its ordinary receiver, and the edited receiver stays on the JPEG. All 18
  schema-2 activation/lookup guards pass. Four original captures and desktop/mobile reports are
  inspected. [Tickets 53](../../.scratch/rich-messages/issues/53-rich-photo-observation.md) and
  [55](../../.scratch/rich-messages/issues/55-rich-photo-late-completion.md) retain the private
  observer contract and native evidence. Rich full-image keys have no size filter; an auxiliary
  leading photo may use one coalesced or two destination-specific original loads.
- The real-bot lifecycle passes fresh phase-local native GET/transfer/cache assertions in 81.59
  seconds, including original rich-photo destination cleanup and a real JPEG reload on restart.
  Four original captures and desktop/mobile reports are inspected. The separate unchanged-photo
  control passes in 66.42 seconds: both COLD launches render the full photo/caption, original
  destination bytes survive, and restart makes no new asset GET. Its two captures and desktop/mobile
  report are inspected. [Ticket 56](../../.scratch/rich-messages/issues/56-photo-lifecycle-cache-oracle.md)
  preserves the corrected non-scrollable-list framing red and fresh acceptance.
  Earlier retained lifecycle acceptance and failed JUnits remain preserved. Wider regression on
  the current APK is still required: 53 normal tests now collect (510 core tests deselected).
  The old normal16 inventory cannot certify later patches.
- Pinned [HTML formatting research](html-formatting-references.md) is integrated and
  [ticket 25](../../.scratch/rich-messages/issues/25-html-source-contract.md) is resolved. The Bot API
  still rejects parse modes. Parser output, cleaning, range repair and automatic entity detection
  are distinct stages; feeding raw HTML entities into the existing validator is insufficient.
- [Quoted code/pre correction](quoted-code-formatting.md) is integrated in core and the normal
  Android adapter. Public World/real-bot and original rendering/edit/restart checks pass. The
  later 27-case continuation reports all passes, but its combined acceptance was invalidated by
  a wrong host editable import. The same qualification applies to the isolated list control.
  Earlier core and focused quoted-code rendering precede the environment change. Original disk
  and late-launch failures remain recorded. The corrected 45-case normal16 gate now passes;
  tickets 26/27 are resolved without reusing contaminated results.
- [Polling startup](../../.scratch/update-delivery/issues/03-polling-startup-reset.md) and
  [structured rich-link core](rich-links-contract.md) are integrated. After repairing the editable
  install, 144 combined feature tests pass, including independent contained bots and public
  captures. The pre-media checkpoint passed 447 core tests at 81.18% coverage. URL/email/phone metadata and labels
  are preserved; automatic detection, mentions, custom emoji and media remain separate needs.
- The native rich-link patch is integrated and compiled. Normal14 passes its baseline codec and rejects
  the valid link scene in a 60.26-second dedicated red run with the corrected import guard.
  All 43,268 reference source files compare with exactly two adapter differences; normal15
  incremental offline compilation passes in 2 minutes 48 seconds. Native acceptance then finds
  missing link fields produce no JSON result. [Ticket 32](../../.scratch/rich-messages/issues/32-rich-link-required-fields.md)
  adds required-field checks in patch 0016; the reviewed fix compiles offline in 1 minute 59 seconds.
  Both focused native tests pass in 135.98 seconds: all 11 valid/29 malformed codec cases and
  real-bot original rendering/live edit/cold restart. Three original PNGs and desktop/mobile
  reports were inspected. The remaining 43 cases pass in 2525.72 seconds on the same normal16
  APK. Independent reconciliation proves exact 45-case coverage with unchanged source, APK,
  profiles and imports. Tickets 30/31/32 are resolved. No destination is opened.
- [Checkout import preflight](../../.scratch/developer-tooling/issues/11-checkout-import-preflight.md)
  rejects another worktree's editable package before test collection. Always provision through
  the assigned checkout's `tools/dev`; inherited `UV_PROJECT_ENVIRONMENT` caused the invalid runs.
- [Local custom emoji](custom-emoji.md) has the schema-7 immutable catalog, public lookup/download,
  atomic retained grants, version-4 dependencies and a passing original lifecycle/animation/cache
  gate. Normal24 also passes 99 native emoji codec, 28 photo codec and 75 mention codec cases.
  Tickets63/65 supply the real-bot lifecycle; settings79, sampled oracle80 and capture83/86 now
  have fresh native acceptance. Ticket66 fault/shared-transfer acceptance remains failed and
  has accepted diagnostic checkpoints in ticket87; ticket89 addresses the confirmed test transport timeout. Semantic captures and virtual callback
  fixes under tickets67/68 pass core checks; ticket69 covers the combined current-message public
  Android path and its complete native expected history/event assertions.
- [Public rich-button targeting](scenario-rich-buttons.md) follows the frozen
  [implementation contract](rich-button-implementation-contract.md). Core, simulation, concurrency
  and abrupt-recovery checks pass. Normal26 preserves reconstructed provenance through actual
  native buffers and SQLite; normal27 preserves original drawing/input while normalizing observer
  coordinates. Seven actual matrix/context cases and the uninstrumented six-visible-control native
  scenario now pass. Ticket74 still needs independent native clipboard paste, complete state/event
  comparisons and wider placement/recovery. Its current status-only test does not prove the later
  unrelated callback succeeded; retained runs reject that operation after a geometry change.
- [Custom-emoji source contract](../../.scratch/rich-messages/issues/28-custom-emoji-source-contract.md)
  is integrated. The [memo](custom-emoji-references.md) separates logical emoji IDs from media file
  identities and requires a resolvable original Document plus local static/animated bytes.
  The synthetic catalog and shared delivery direction are approved; freeze exact schemas and
  verify resolution/failure behavior during implementation. See the newer catalog, codec and original native lifecycle checkpoint above.
  The [concrete catalog proposal](custom-emoji-proposal.md) preserves caller-selected IDs and
  message fallback text, separates bot file identities from recipient document/media access,
  and requires transparent VP9 WebM. Original WebP/WebM fixtures are integrated with independent
  browser decoding, exact lossless WebP colors, four transparent video frames and a one-second
  duration. Initial color/duration failures are preserved. The catalog and shared media
  architecture are approved; fixture decoding is not original Android playback.
- [Default rich detection](rich-auto-detection.md) is a separate operational gap: the pinned
  open source forwards a server autolink flag and does not establish enrichment grammar or
  nesting/block rules. Do not treat ordinary-text detection as proof; a local fidelity policy
  needs consultation. No account/DC observation is authorized.
- [Explicit rich mentions](rich-mention-proposal.md) have approved identity rules:
  bot-contact admission, authoritative User projection, message-derived recipient visibility and
  versioned identity dependencies before native message application. Core/API/v3 projection is
  integrated: authoritative profiles, atomic admission, response-specific disclosure and frozen
  legacy callback retry checks pass. The combined core gate passes 496 tests at 81.98% coverage
  in 64.12 seconds at that checkpoint. Normal22 compiles offline in 2m13s and passes all 75 native
  mention codec cases plus the 28 photo codec cases. Normal23 passes the contained real-bot
  original UI scenario: initial A, two inline taps, first live B disclosure, removal and COLD
  restart in 102.02 seconds. Four original images and desktop/mobile reports are inspected;
  ticket 54 is resolved. That checkpoint's combined core gate passed 498 tests at 81.98% in 69.17 seconds.
  Wider native regression remains required; automatic detection and navigation are separate.
- Public rich-button targeting now has a [concrete proposal](rich-button-targeting-proposal.md):
  canonical paths, journal revisions, client-lifetime-bound single-use targets, explicit uncertain
  outcomes and client-local copy effects. Independent review and a guarded same-clock edit
  experiment inform the approved contract. The shared [implementation contract](rich-button-implementation-contract.md) is now frozen.
  The permanent GPL observation seam and public effects have the focused native checkpoint above;
  wider independent acceptance remains open. Earlier experiments do not certify the public seam.

Preserve the full scope while pursuing independent work during a pending decision. No external
runtime egress or remote publication is authorized. Provisioning and primary-source research are
separate from bot/client execution; never contact production/Test DCs or use real accounts.

## Accepted checkpoint and verification limits

| Surface | Current evidence and next boundary |
| --- | --- |
| Normal rich messages | Structured blocks, inline formatting, effects, lists and callback/copy/disabled representation reach the original renderer. See [rich API](rich-messages.md), [projection](android-rich-projection.md), [list sources](rich-list-references.md) and [actions](rich-buttons-contract.md). Media and broader content remain open. |
| Normal Android inventory | The same immutable normal16 APK covers all 45 cases: two focused passes plus 43 continuation passes, with exact inventory/source/APK/profile/import equivalence independently verified. This is resumed coverage, not one uninterrupted run. Earlier invalidated results are excluded; see [acceptance](../../.scratch/rich-messages/issues/31-rich-links-acceptance.md). |
| Experimental callbacks | Two observed original controls receive one ordinary tap each; real bot answers/edits, complete native/API/history/event comparisons, cold restart, absent/wrong opt-in, zero accounts and isolation pass. Six original PNGs and desktop/mobile report inspected. The 83.83-second run is separate from the normal inventory. See [experiment](rich-action-input-experiment.md). |
| Experimental copy/disabled | Exact original clipboard text survives ordinary paste/delete; disabled input leaves World/API unchanged; restart passes. All native assertions pass in 98.39 seconds, but pytest fails only because report packaging exceeds eight images. Retained complete-result revalidation and two bounded reports pass in 0.28 seconds with original evidence unchanged. Do not relabel the original JUnit green. Callback regression on the new experimental APK passes in 101.82 seconds. All 13 effect PNGs, six callback PNGs and four report captures inspected. See [effects experiment](rich-action-effects-experiment.md). |
| Latest core | 917 passed at 87.07% coverage in 145.42 seconds using four isolated workers, verified primary imports and no simultaneous guest. Includes raw capture and bounded fault diagnostics; native acceptance remains separate. |
| Latest static/workflow | The 917-test checkpoint passes 53 documented static commands, Ruff lint/format across 474 files and configuration/links in 233 Markdown documents. The unchanged pinned workflow check passed at the preceding checkpoint. Workers88/89 are not integrated. |
| Media preparation | Four original PNGs decode independently with exact dimensions/corners. A pinned original 64×48 JPEG also reproduces byte-for-byte; independent browser decoding checks all 512 interior pixels with maximum RGB channel error 1. Both truncated photo formats reject. Original [custom-emoji fixtures](../../tests/assets/custom-emoji/README.md) repeat byte-for-byte under the recorded encoder profile and pass FFmpeg plus independent Chromium decoding, full alpha geometry, WebP colors, WebM frames/duration and invalid-input rejection. The optional pinned media shell now records FFmpeg 6.1.6, libvpx 1.16.0 and libwebp 1.6.0, reproducing all four emoji binaries unchanged. This establishes fixtures/contracts, not media API or native media/emoji support. |

The normal and experimental APKs are distinct. Preserve their ignored provenance and immutable
fingerprints; experimental geometry is absent from the normal patch series. Current experimental
coverage is short LTR row/inline callbacks, copy row and disabled inline. RTL/nesting, duplicate or
stale input, offscreen/long-press behavior and atomic observation/input remain open.

The old native continuation, repeated old-APK red, core, static and workflow checks are terminal.
Normal15/16 builds, required-field reds, focused native acceptance and report preview are terminal.
The remaining43 native suite and independent combined-coverage verification are terminal and
passing. Original custom-emoji fixture checks and browser review are terminal; the worker branch
is frozen and integrated, with coordinator-owned acceptance. The optional media shell is integrated
with guarded reproduction, provenance checks and unchanged runtime/APK fingerprints. Host paths,
handles, fingerprints and artifact locations stay in ignored local notes. Original JPEG worker
checks and independent browser review are terminal and integrated; the PNG files remain unchanged.

## Development throughput

Use `tools/dev media` for pinned fixture generation and verification; see
[environment guidance](environment.md#media-fixtures) and
[ticket 12](../../.scratch/developer-tooling/issues/12-pinned-media-shell.md). Its generated profile
keeps executable paths out of committed manifests. Provision missing check dependencies from a
reviewed binary-cache plan before offline checks; missing outputs can trigger large source builds.

Use the [parallel workflow](parallel-work.md): implementation workers each own a ticket, branch and
separate worktree; coordinator owns merges/conflicts and combined verification. Freeze shared
interfaces first. Use appropriate agents, including GPT-5.6 Sol for bounded routine work. Keep
shared handoff, compatibility, lockfiles and architecture docs coordinator-owned.

[CONTRIBUTING.md](../../CONTRIBUTING.md) now gives the established four-worker non-Android core
recipe. Use the pinned [tools/dev](../../tools/dev) environment and outer network guard. Android
builds and serial guests hold their respective shared locks and use separate writable state.
Provision per-worktree dependencies offline from verified caches where possible; see
[environment guidance](environment.md). Avoid rerunning passed gates without changes or failures
that warrant them. [Retained timings/selection](test-timings.md) distinguish wall and summed case
time and select unexecuted cases only after independently verifying unchanged inputs.

Two-worker Android scheduling remains unaccepted: a concurrent cold-launch failure and unchanged
passing serial control do not establish the cause. Bounded timestamped startup diagnostics now
retain UWB initialization failure/success evidence; causality and latency contribution remain
unproven. Follow [ticket 06](../../.scratch/developer-tooling/issues/06-parallel-native-gate.md) and
[ticket 07](../../.scratch/developer-tooling/issues/07-guest-startup-diagnostics.md) when new planned
guest work supplies relevant observations. Keep profiles/timeouts unchanged without justification.

## Earlier evidence and progress records

The preserved [historical handoff](handoff-history.md) contains prior checkpoint details and failed
trials. Consult it when investigating an earlier milestone; its next-action instructions are
historical. Relevant active references include [composer work](../../.scratch/programmatic-scenarios/issues/04-native-composer.md),
[transport diagnosis](android-transport-reliability.md), [live-gap recovery](live-gap-recovery.md),
[consumer runner](consumer-runner.md), [scenario SDK](scenario-sdk.md) and
[rendering profile](android-effects-profile.md).

Update individual local tickets, the compatibility matrix and this current handoff with verified
outcomes and the next action. Keep historical evidence in linked task documents rather than
appending another chronological checkpoint here. Commit authorized local work; remote publication
and consequential design/license/network/fidelity changes still require consultation.
