# Resolve update filtering and negative-offset contracts

Type: research
Status: ready-for-agent
Work state: resolved
Blocked by: none

Own only docs/development/update-delivery-references.md and this ticket. Inspect official Bot API
10.3 documentation and server sources, resolving immutable revisions where available. Determine
whether allowed_updates changes existing queues or future enqueueing, persistence/default/reset
behavior, valid type names and malformed inputs, offset semantics, and long-poll interactions.
Write original cited findings; do not copy upstream implementation into the core. Report unknowns.

The coordinator owns implementation, shared docs and integration. Do not run bots or Android.

Findings are recorded in [update delivery references](../../../docs/development/update-delivery-references.md).
Resolved the official 10.3 version commit and its TDLib gitlink, future enqueue filtering,
lenient filter parsing, persistent selection, count-based negative offsets and empty-poll
normalization. Documented conditional poll interruption and distance-dependent positive-offset
behavior as source qualifications. Static source research only; no live-server or Android claims.
Verification: inspected cited immutable files, checked local links and `git diff --check`.
Implementation and combined behavioral verification remain the coordinator's responsibility.
