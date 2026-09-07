# Compatibility matrix

An experimental [world/Bot API subset](../development/world-bot-prototype.md) now has local
real-process evidence. [Synthetic Android startup](../development/android-application.md) renders
a real plain-text bot exchange in the pinned client. The [Android callback loop](../development/android-callbacks.md)
adds a real tap, callback answer, visible edit and bounded restart recovery. Broader rendering fidelity and external
Bot API conformance remain unverified. This is a
starting inventory, not an exhaustive or authoritative catalog of
Telegram's current methods. Expand it from official sources at the selected version.

Ticket 01 now has [source feasibility findings](../development/android-source-feasibility.md)
and a [prototype proposal](../development/android-foundation-proposal.md). The source commit and
API baseline are approved prototype targets; partial rows below refer only to local implementation. Host
KVM/network-namespace probes establish neither Android support nor scenario egress enforcement.

The [Linux process boundary](../development/runtime-boundary.md) now has real isolation and
cleanup tests. [Private bot components](../development/component-boundary.md) retain separate
files/processes on the same offline run network, including bot restart in the Android callback
case. The emulator now has separate files/processes, with KVM requiring explicit outer and child
opt-in. Resource quotas and per-component port restrictions remain open. These isolation tests
do not establish Telegram rendering or protocol conformance.

| Surface | Required evidence before claiming support | State |
| --- | --- | --- |
| HTTP request transport | Equivalent JSON/form/query requests, Unicode, malformed-input rejection and real consumers | Partial: [UTF-8 JSON, forms and query parameters](../development/bot-request-encoding.md), serialized keyboard/entities and textual callback Booleans; multipart uploads planned |
| Programmable scenarios | Private scenario execution, real consumer bots, shared world authority and reusable runner | Partial: [Python client](../development/scenario-sdk.md), [consumer runner](../development/consumer-runner.md), explicit files, concurrent runs and failure reports; [shared simulation/headless captures](../development/scenario-captures.md); [native inline-button input](../development/scenario-input.md), [bot stop/recovery](../development/scenario-lifecycle.md) and [bounded Start Bot/typed input](../development/scenario-composer.md); interactive mode, broader composer semantics and expanded dependencies pending |
| Polling/webhooks | Actual consumer bot, update delivery/acknowledgment, retries and conflicts | Partial: local short/long polling, acknowledgment, disconnect/restart retries, [persistent selection and negative offsets](../development/update-delivery.md); stricter integer validation and differing poll-conflict/distant-positive-offset behavior; expiry and webhooks planned |
| Messages/commands/deep links/replies | Full requests, entities, state effects and Android behavior | Partial: private HTTP exchange and actual Android rendering; nine explicit non-link formatting types, formatting-only edits and latest-message restart verified locally; links, parse modes, commands and replies planned |
| Callback/reply keyboards | Real tap, callback answer, duplicate/stale/wrong-actor behavior | Partial: callback-only keyboards, real Android tap/answer/edit, durable queries and HTTP stale/duplicate/wrong-actor checks; other button types planned |
| Native composer | Actual Unicode input, scoped send correlation, client acknowledgment, bot reply and interruption recovery | Partial: [native case](../development/android-composer.md) verifies distinct equal-text sends, stale-draft rejection and restart after response loss; [acknowledgment before storage](../development/ack-storage-recovery.md) verifies recovery with the original ID-remap method held; [scenario input](../development/scenario-composer.md) adds matching simulation/Android Start Bot and bounded formatted text; [live-gap recovery](../development/live-gap-recovery.md) passes equal/distinct timestamps and a two-page, 1,000-message backlog while polling is held; [transport corrections](../development/android-transport-reliability.md) pass the 11 focused native checks, while the preceding full gate stopped on a startup timeout before input; the expanded 28-test gate now passes; broader transformations, concurrent recovery and further interruption points pending |
| Inline queries/results | Supported private/group/channel combinations and client result rendering | Planned |
| Contexts/permissions | Private/group/supergroup/channel, privacy, admin, block/remove, migration, topics | Partial: private bot/chat capability checks |
| Rich messages | Versioned API exposure, actual Android rich blocks/buttons/media and RTL | Partial: [structured send/edit API](../development/rich-messages.md), twelve block types and nine formatting wrappers; [native serialization catalog and original bilingual/RTL send/edit/restart captures](../development/android-rich-projection.md); explicit detection skip required; parse modes, automatic entities, links/media/custom emoji/drafts pending; [callback/copy/disabled rich buttons](../development/rich-buttons-contract.md) pass core/API and simulation capture checks, and focused native codec/rendering/live RTL edit/cold-restart checks; combined Android regression is running and rich-button input remains pending; list World/API, native codec/checkbox/edit/restart and public inline callback/ambiguity checks pass with the 38-case list-inclusive Android gate; subsequent [rich-string cleaning](../development/rich-text-cleaning.md) passes 91 World/HTTP cases, the real-bot regression, the 336-test core gate and a separate focused native serialization/live RTL edit/cold-restart check with three inspected original captures; [public rich captures](../development/scenario-rich-messages.md) pass in both modes, [native rich inline targeting](../development/scenario-input.md) passes real callback/edit and ambiguity checks in the preceding 34-test Android gate |
| Media/files/albums | Local upload/download lifecycle, malformed assets, size/caption constraints | Planned |
| Custom/premium emoji | Entity correctness, licensed local documents, rendering, entitlement/fallback models | Planned |
| Polls/quizzes/reactions | Legal/illegal transitions, update types and actual interaction rendering | Planned |
| Mini Apps | Actual local app, Android WebView host bridge, launch/auth fixtures and egress blocking | Planned |
| Business/payments/Stars/gifts | Source-derived scope; explicit local simulation vs unsupported settlement | Planned |
| Localization | User/chat/bot/client language combinations; Persian/English, RTL/LTR and text expansion | Planned |
| Recovery/concurrency | Restart persistence, deterministic replay, same-world races and cross-world isolation | Partial: SQLite reopen/migration, atomic persona snapshots/cursors, concurrent writers and bot queue isolation; real tap followed by bot SIGKILL/replay; latest and older cached replies recover after Android restart, including edits during downtime; deletion, multi-dialog and partial mutation recovery planned |
| Faults/limits | Documented validation plus labeled injections, byte/UTF-16 limits, 429/delay/ambiguous outcomes | Planned |
| Previews/help examples | Actual renderer exports tied to scenarios and labeled synthetic conversations | Partial: [scenario chat captures](../development/scenario-captures.md) retain original Android PNGs and semantic checkpoints in reports; live viewing, stitched histories and export presets pending |
| Performance/reports | Reproducible workloads, separated latency sources, HTML evidence and redaction | Partial: [self-contained recovery report](../development/reports.md) with original Android screenshots and measured app-launch times; [consumer runner](../development/consumer-runner.md) retains redacted pass/failure/timeout evidence; workload percentiles and separated latency diagnosis planned |

Track fidelity on two separate axes: implementation state (planned/implemented) and evidence
(documented/observed/verified/approximate/unsupported). Each claim needs exact versions, a scenario,
source provenance and evidence artifacts. Passing the simulator's own tests alone cannot establish
external Telegram conformance.
