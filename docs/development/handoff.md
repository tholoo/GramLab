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

## First action

Read [AGENTS.md](../../AGENTS.md) and the assigned ticket. Follow its linked testing, architecture,
offline safety, licensing and completion requirements before the corresponding action.

- Photo delivery awaits user consultation in [ticket 24](../../.scratch/rich-messages/issues/24-rich-photo-design-review.md).
  The [concrete proposal](rich-photo-proposal.md) recommends multipart uploads/reuse, World-owned
  immutable bytes and authenticated delivery through original Android FileLoader. Source research
  and independently decoded original PNG fixtures are merged. Asset storage, file APIs and native
  media delivery are absent. A goal continuation alone is not approval of these decisions.
- Pinned [HTML formatting research](html-formatting-references.md) is integrated and
  [ticket 25](../../.scratch/rich-messages/issues/25-html-source-contract.md) is resolved. The Bot API
  still rejects parse modes. Parser output, cleaning, range repair and automatic entity detection
  are distinct stages; feeding raw HTML entities into the existing validator is insufficient.
- [Quoted code/pre correction](quoted-code-formatting.md) is integrated in the core and normal
  Android adapter. Public World/real-bot regression checks and original rendering/edit/restart
  pass. The broader 43-case Android inventory has eight passes across retained focused and
  continuation runs; the next case failed at emulator startup for insufficient disk space.
  Preserve results, reclaim only proven disposable runtime state and continue the remaining
  identities. Tickets 26/27 remain claimed until combined verification finishes.
- [Custom-emoji source contract](../../.scratch/rich-messages/issues/28-custom-emoji-source-contract.md)
  is ready for bounded independent research while native verification continues. It establishes
  input/document/asset requirements; no custom-emoji runtime support is claimed.
- Public rich-button targeting remains open. The callback and copy/disabled experiments below
  establish bounded original input, not a stable public geometry API. Prepare a concrete proposal
  before consequential targeting/navigation changes.

Preserve the full scope while pursuing independent work during a pending decision. No external
runtime egress or remote publication is authorized. Provisioning and primary-source research are
separate from bot/client execution; never contact production/Test DCs or use real accounts.

## Accepted checkpoint and verification limits

| Surface | Current evidence and next boundary |
| --- | --- |
| Normal rich messages | Structured blocks, inline formatting, effects, lists and callback/copy/disabled representation reach the original renderer. See [rich API](rich-messages.md), [projection](android-rich-projection.md), [list sources](rich-list-references.md) and [actions](rich-buttons-contract.md). Media and broader content remain open. |
| Normal Android inventory | The same immutable 13-patch APK covers all 41 cases: 19 retained passes plus 22 continuation passes after correcting the old preformatted-tab fixture. This is resumed coverage, not one uninterrupted green run. See [ticket 20](../../.scratch/rich-messages/issues/20-canonical-catalog-regression.md). |
| Experimental callbacks | Two observed original controls receive one ordinary tap each; real bot answers/edits, complete native/API/history/event comparisons, cold restart, absent/wrong opt-in, zero accounts and isolation pass. Six original PNGs and desktop/mobile report inspected. The 83.83-second run is separate from the normal inventory. See [experiment](rich-action-input-experiment.md). |
| Experimental copy/disabled | Exact original clipboard text survives ordinary paste/delete; disabled input leaves World/API unchanged; restart passes. All native assertions pass in 98.39 seconds, but pytest fails only because report packaging exceeds eight images. Retained complete-result revalidation and two bounded reports pass in 0.28 seconds with original evidence unchanged. Do not relabel the original JUnit green. Callback regression on the new experimental APK passes in 101.82 seconds. All 13 effect PNGs, six callback PNGs and four report captures inspected. See [effects experiment](rich-action-effects-experiment.md). |
| Latest core | 411 passed at 81.01% coverage in 70.49 seconds using four isolated workers, with Android excluded. No production performance conclusion follows from test scheduling. |
| Latest static/workflow | All 22 documented static commands, 143 configuration/local-link checks and pinned offline workflow check pass after quoted-code integration. The later report-unit correction passes focused static and retained-result validation; corrected desktop/mobile reports were inspected. |
| Media preparation | Three original PNGs decode independently with exact dimensions/corners; truncated fixture rejects. Deterministic generation/static checks pass. Pinned [photo source research](rich-photo-references.md) is integrated. This establishes fixtures/contracts, not media API or native photo support. |

The normal and experimental APKs are distinct. Preserve their ignored provenance and immutable
fingerprints; experimental geometry is absent from the normal patch series. Current experimental
coverage is short LTR row/inline callbacks, copy row and disabled inline. RTL/nesting, duplicate or
stale input, offscreen/long-press behavior and atomic observation/input remain open.

The quoted-code native continuation stopped after six passes and one disk-space startup failure;
its JUnit remains failed. The two focused passes are retained separately. Build/core/check/preview
processes are terminal. Inspect current agent state and exact process handles before dispatch or
resume. Host paths, handles, fingerprints and artifact locations stay in ignored local notes.

## Development throughput

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
