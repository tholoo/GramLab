# Control a world from private scenario code

Type: task
Status: ready-for-agent
Work state: claimed

Expose explicit existing world operations over authenticated local JSON. The trusted owner issues
a fresh run-control capability; it is distinct from bot/persona credentials and bound to one
world. No reflection, arbitrary code execution, file paths or credential issuance is exposed.

## Acceptance

- Real HTTP from a private component creates participants/chats, performs virtual actions and
  reads complete world state and ordered events while the database remains inaccessible.
- A real independently running bot participates through the existing Bot API.
- Wrong/missing/repeated credentials, wrong worlds, unknown operations and malformed input fail
  without effects. The same control interface cannot issue bot or client credentials.
- Responses explicitly identify protocol version and world; access logs never retain capabilities.
- A lost mutation response is surfaced as uncertain and never automatically retried. Durable
  request deduplication/replay remains separate work, not an implied guarantee.

Use the agreed HTTP, public world and Linux runtime test seams. Keep the control implementation
internal until the runnable consumer workflow exists.

## Progress

2026-09-06: The [control implementation](../../../docs/development/scenario-control.md) now
exposes nine explicit world operations with ephemeral run credentials, envelope validation and
stable world identity. A private scenario process drives a separate real bot without database or
bot-file access and with rejected external traffic. Tests catch directory replacement, incomplete
HTTP mutation, malformed envelopes, callback retries and concurrent writers in two worlds. The
full core gate passes 91 tests at 92.07% coverage. Report redaction recognizes control credentials.
The SDK transport/uncertain-outcome exception remains the next step, so this ticket stays claimed.
