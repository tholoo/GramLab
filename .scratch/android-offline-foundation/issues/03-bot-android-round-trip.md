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

2026-09-06 request-encoding follow-up: extend the existing HTTP boundary to accept standard
URL-encoded forms and serialized complex parameters under the selected Bot API 10.3 baseline.
Verify complete responses and world effects, rejected malformed/ambiguous input and the real
bot/Android path. This changes transport decoding within the approved model; broader method,
media and framework compatibility remain separate requirements.

Encoding follow-up verified: [HTTP evidence](../../../docs/development/bot-request-encoding.md)
now covers UTF-8 forms/query/JSON, serialized keyboard/entities and textual callback Booleans.
The invalid UTF-16 poll baseline incorrectly acknowledged pending updates; the corrected decoder
rejects it without state changes. All 82 core tests pass at 91.99% coverage, and a fresh actual
Android formatting/edit/restart scenario passes with the real form-encoded bot. The client/APK
is unchanged. This is partial compatibility progress; the full ticket acceptance remains open.
