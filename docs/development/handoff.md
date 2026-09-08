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

This checkpoint supersedes the older native blockers described below. The full operational
milestone remains incomplete; the last combined core gate is still 780 passed at 86.71% coverage.

- Normal26 fixes reconstructed rich-button provenance. Independent execution against actual
  Android native buffers and SQLite passes all 25 reload, reopen, stale-update, A→B→A and
  malformed-record cases; the same probe demonstrates the original normal25 identity loss.
- Public native targeting now returns all eight canonical targets. Two host readiness fixes
  pass 88 focused checks and let the subsequent diagnostic execute the actual row callback and
  original row copy. A disabled row opens Telegram's original message context menu; its popup
  focus makes confirmation uncertain and blocks later targets. Preserve that original behavior.
  App-owned popup confirmation requires actual ownership evidence, not a matching title.
- Normal27 applies the coordinate observer's explicit cell-local matrix normalization without
  changing original rendering or touch propagation. Its zero-fuzz/offset two-file application
  and complete offline build pass; native matrix regression and combined public acceptance
  remain pending under tickets82/84.
- Original custom-emoji UI06 completes real bot edit, original settings enable, native animation
  download and unchanged cold restart. The reviewed sampled visual checker passes 32 focused
  controls and full immutable retained lifecycle revalidation, including all 72 burst frames,
  exact cache bytes and isolation. The separate report is inspected at desktop/mobile sizes;
  the original failed JUnit remains failed. Fresh UI07 also completes the lifecycle but rejects
  one 500.3 ms capture interval. Ticket83 batches original guest screenshots before transfer to
  remove host transfer latency from sampling; its fresh native acceptance remains pending.
- Immutable archived APK tooling passes 20 integrated filesystem cases and scoped static checks;
  contributor/CI checks include it. It performs no automatic cleanup. Ticket15 prepares a small
  private-only Android patch staging helper to replace repeated version-specific scripts.

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
- [Local custom emoji](custom-emoji.md) now has integrated schema-7 immutable catalog, public
  Bot API lookup/download, atomic retained grants and v4 dependencies. Focused integrated checks
  pass 30 media, 31 catalog/API, 31 native request-proxy and four initial scenario cases. The
  original source predicate has pinned BSL provenance. Seven catalog isolation regressions and eight dropped-response/
  contained-runner tests are integrated and pass focused checks. The observed integer-ID document-route
  admission mismatch is corrected under ticket64, with its original red preserved. The combined
  gate now passes all 652 core tests at 85.44% coverage in 87.04 seconds. A prior overlapping
  core/Android run passed 614 and timed out during the existing large-report scenario; that
  unchanged case passes alone in 3.09 seconds. Preserve the red; contention is not yet proven
  causal. A rebuilt normal24 adapter passes all 99 native codec cases in 144.279 seconds, after
  a probe-only FileLoader-thread exit correction; original red and diagnostic evidence are retained.
  The same APK passes the two existing photo/mention codec tests (28 and 75 vectors) in
  254.284 seconds. A diagnostic screenshot visibly renders four static emoji, but a false
  accessibility readiness check stops the run before edit/restart. Static lifecycle acceptance,
  transparent animation, cache reuse and fault recovery remain open.
  Ticket63 supplies the compact real-bot fixture. Ticket65 has seven integrated pixel-oracle
  tests and an original-settings diagnostic. The latest guest reaches the original emoji animation
  settings but fails after an unchanged unchecked control; ticket79 corrects bounded diagnostic
  input and retains preferences on failure. Animation and cold-cache acceptance remain open.
  Ticket66 has seven integrated HTTP/staging/diamond tests for static resolver faults and shared
  delivery. Both native acceptance gates remain pending. Public semantic capture and virtual
  callback compatibility fixes are integrated under tickets67/68: eight capture controls and
  two callback controls pass focused checks and the combined core gate. Two
  Android host defects (composer snapshot version and photo caption matching) are corrected
  under ticket69. Seven integrated host/capture/callback controls and scoped static checks pass;
  the combined core gate also passes. The collected native scenario remains unexecuted.
  The [rich-button implementation contract](rich-button-implementation-contract.md) is frozen
  under ticket70 after independent source/recovery review. It preserves strict v4 payloads and
  specifies a separate app-private observation protocol. Tickets71/72/74 divide core primitives,
  GPL observation and independent public acceptance; the coordinator owns integration73.
  The [public rich-button operations](scenario-rich-buttons.md) are now implemented: independent
  simulation and actual abrupt supervisor recovery pass together, and the integrated Android host
  passes 101 boundary/integration checks. Subsequent review fixes pass 41 registry/journal/recovery
  checks, including malformed lifetime and deeply nested corruption. The combined core gate
  passes 780 tests at 86.71% coverage in 99.12 seconds; full lint/format, scoped strict typing,
  213-document link validation and the pinned offline workflow check pass. These host tests substitute
  external guest files. Patch25 has passed independent source review and exact zero-fuzz/offset
  application; the complete normal25 offline APK build passed in 3 minutes 1 second with strict dependency
  verification and a verified APK signature. Native targeting, original
  clipboard paste and wider placement/regression acceptance remain pending. The existing normal24
  custom-emoji APK/provenance and exact changed source preimages are retained separately.
  Actual normal25 execution exposed two host startup defects: ADB shell quoting and the window
  focus query. Their narrow fixes pass 87 integrated host/public checks. The corrected original
  viewport visibly shows row and inline controls, but no observation is published. An actual
  Android TL round trip confirms reconstructed button objects lose their identity bindings.
  [Ticket77](../../.scratch/rich-messages/issues/77-rich-button-native-persistence.md) implements
  exact revision provenance through existing message-local storage; independent
  [ticket78](../../.scratch/rich-messages/issues/78-rich-button-native-storage-regression.md)
  checks SQLite reload, reopen, stale metadata and A→B→A. These are active fixes, not native acceptance.
- [Custom-emoji source contract](../../.scratch/rich-messages/issues/28-custom-emoji-source-contract.md)
  is integrated. The [memo](custom-emoji-references.md) separates logical emoji IDs from media file
  identities and requires a resolvable original Document plus local static/animated bytes.
  The synthetic catalog and shared delivery direction are approved; freeze exact schemas and
  verify resolution/failure behavior during implementation. See the newer catalog/codec checkpoint above; native rendering is still unproven.
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
  The permanent GPL observation seam and public effects are implemented but native acceptance
  is blocked by the storage identity defect above. The earlier experiments do not certify them.

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
| Latest core | 780 passed at 86.71% coverage in 99.12 seconds using four isolated workers, verified primary imports and no simultaneous guest. Subsequent startup/fixture corrections pass focused integration; repeat the combined gate after the current fix batch. |
| Latest static/workflow | The 780-test checkpoint passes full Ruff lint/format across 448 files, production/scoped strict typing, 213-document link validation and the pinned offline workflow check. Later worker changes still need combined verification. |
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
