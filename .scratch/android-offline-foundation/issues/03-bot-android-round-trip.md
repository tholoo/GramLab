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
