# Compatibility matrix

Every runtime row is **planned, unimplemented, unverified**. There is no pinned client profile or
Bot API version yet. This is a starting inventory, not an exhaustive or authoritative catalog of
Telegram's current methods. Expand it from official sources at the selected version.

| Surface | Required evidence before claiming support | State |
| --- | --- | --- |
| Polling/webhooks | Actual consumer bot, update delivery/acknowledgment, retries and conflicts | Planned |
| Messages/commands/deep links/replies | Full requests, entities, state effects and Android behavior | Planned |
| Callback/reply keyboards | Real tap, callback answer, duplicate/stale/wrong-actor behavior | Planned |
| Inline queries/results | Supported private/group/channel combinations and client result rendering | Planned |
| Contexts/permissions | Private/group/supergroup/channel, privacy, admin, block/remove, migration, topics | Planned |
| Rich messages | Versioned API exposure, actual Android rich blocks/buttons/media and RTL | Planned |
| Media/files/albums | Local upload/download lifecycle, malformed assets, size/caption constraints | Planned |
| Custom/premium emoji | Entity correctness, licensed local documents, rendering, entitlement/fallback models | Planned |
| Polls/quizzes/reactions | Legal/illegal transitions, update types and actual interaction rendering | Planned |
| Mini Apps | Actual local app, Android WebView host bridge, launch/auth fixtures and egress blocking | Planned |
| Business/payments/Stars/gifts | Source-derived scope; explicit local simulation vs unsupported settlement | Planned |
| Localization | User/chat/bot/client language combinations; Persian/English, RTL/LTR and text expansion | Planned |
| Recovery/concurrency | Restart persistence, deterministic replay, same-world races and cross-world isolation | Planned |
| Faults/limits | Documented validation plus labeled injections, byte/UTF-16 limits, 429/delay/ambiguous outcomes | Planned |
| Previews/help examples | Actual renderer exports tied to scenarios and labeled synthetic conversations | Planned |
| Performance/reports | Reproducible workloads, separated latency sources, HTML evidence and redaction | Planned |

Track fidelity on two separate axes: implementation state (planned/implemented) and evidence
(documented/observed/verified/approximate/unsupported). Each claim needs exact versions, a scenario,
source provenance and evidence artifacts. Passing the simulator's own tests alone cannot establish
external Telegram conformance.
