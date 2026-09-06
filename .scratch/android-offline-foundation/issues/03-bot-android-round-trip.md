# Complete a real bot and Android interaction round trip

Type: task
Status: needs-info
Work state: open
Blocked by: 02

Connect a minimal framework-independent local Bot API consumer to the same world used by Android.
Implement only the methods required by the milestone with real validation and explicit errors.

## Acceptance

- The actual bot receives a generated user update and responds through the HTTP boundary.
- Its message and button appear through upstream Android rendering, not a recreated chat view.
- A real client tap generates the appropriate bot update, and the bot's edit appears in Android.
- Simulation-only and Android executions agree on semantic state for the same scenario.
- Include duplicate/stale/wrong-actor and malformed entity/byte-limit cases where applicable.
- Exercise English/Persian combinations, and inspect the selected rich-message/media/emoji case
  with explicit supported/unsupported evidence.
- Save screenshots and structured assertions tied to the pinned fidelity profile.

## Comments

Bot API and client object mappings need independent expected fixtures. The server model must not
silently accept unsupported operations simply to satisfy the UI.

2026-09-06 partial evidence while ticket 02 remains active: the
[actual callback loop](../../../docs/development/android-callbacks.md) now drives an accessible
inline button through a real Android tap, a killed/restarted bot, live edit and answer, then a
client cold restart. Simulation-only and Android share exact semantic expectations. The selected
rich-message/media/emoji case, broader language combinations and ticket 02's remaining safety
acceptance are still open; this does not close this ticket.
