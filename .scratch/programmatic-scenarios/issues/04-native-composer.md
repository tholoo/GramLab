# Native composer sends and durable client recovery

Type: task
Status: ready-for-agent
Work state: claimed
Blocked by: none (03 resolved)

The coordinator owns the world/bridge, GPL adapter patch, scenario integration, tests and handoff.
Implement the approved semantic request/cursor boundary using the
[pinned composer references](../../../docs/development/android-composer-references.md).
Keep the actual composer, send helper, controller and renderer. No DC/account use or alternate UI.

## Acceptance

- Authenticated text sends commit one message, event and bot update with durable request correlation
  scoped to persona and destination. Retry after lost response returns the original committed result.
- Per-persona message positions are independent of the world journal and survive migration/restart.
  Snapshot, live updates and difference recovery agree with compact send acknowledgments.
- Unsupported request flags fail before mutation. Wrong persona, destination, world, capability,
  invalid payload and inconsistent request reuse retain explicit errors.
- Actual composer input causes the mutation. Repeated equal text is distinct; accepted retries are
  not. Observe positive IDs, final send state, no pending negative duplicate and real bot replies.
- Exercise event/ack order and interrupted commit/ack/storage boundaries, then cold restart.
  Preserve correlation and the client database, with no placeholder sequence values or hidden gaps.
- Consumer simulation and Android input use the same semantic world contract; retain original
  multilingual captures and complete recovery evidence in the existing reports.
- Run focused boundary regressions before implementation, offline build and the applicable full
  core/Android gates. Preserve the license/patch boundary and update supported surfaces honestly.

The world remains the single authority and Android remains a recoverable replica, as approved in
[ADR 0004](../../../docs/adr/0004-semantic-bridge-and-world-persistence.md). This implements its
request correlation and client cursor obligations; it does not widen into an MTProto server.

Progress: [the independent send boundary](../../../docs/development/client-sends.md) has seven
new behavioral tests, 53 focused passing regressions and a full core gate of 186 tests at 82.55%
coverage. The [focused native case](../../../docs/development/android-composer.md) now passes
actual Unicode sends, distinct equal-text actions, stale-draft rejection, compact acknowledgment
and difference serialization, retained client state across restart, and response-loss-after-commit
recovery with one bot reply. Fresh preparation preserves 6,666 upstream UI/resource files.
The full 20-test Android gate passes, predating the new composer-text contract test, which then
passes its seven fixtures separately. The native
bot-history Seen display rule was verified separately from stored read state; the renderer is
unchanged. Scenario integration, cross-mode composer semantics and additional interruption
boundaries remain in progress; this ticket is not resolved.
