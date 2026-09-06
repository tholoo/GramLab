# Resolve update filtering and negative-offset contracts

Type: research
Status: ready-for-agent
Work state: claimed
Blocked by: none

Own only docs/development/update-delivery-references.md and this ticket. Inspect official Bot API
10.3 documentation and server sources, resolving immutable revisions where available. Determine
whether allowed_updates changes existing queues or future enqueueing, persistence/default/reset
behavior, valid type names and malformed inputs, offset semantics, and long-poll interactions.
Write original cited findings; do not copy upstream implementation into the core. Report unknowns.

The coordinator owns implementation, shared docs and integration. Do not run bots or Android.
