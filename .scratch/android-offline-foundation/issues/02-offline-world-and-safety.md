# Establish isolated synthetic state and enforce offline execution

Type: task
Status: needs-info
Work state: open
Blocked by: 01

Use the approved boundary/runtime from ticket 01. Define the smallest real world and lifecycle
needed for the round trip. Implement public behavior test-first; avoid speculative API stubs.

## Acceptance

- Two independent worlds can create synthetic users/chats with no shared state or credentials.
- Dedicated Android fixture state starts without authentication to any Telegram environment.
- Independent enforcement blocks external network paths from the core, bot and Android runtime.
- Tests demonstrate denied external attempts, allowed local traffic, safe artifact paths and
  scoped cleanup. Merely observing no network call is insufficient.
- IDs, media, update queues and run artifacts are isolated; seeds and clocks are controllable at
  owned boundaries. Record any Android timing limitations explicitly.

## Comments

Promote triage status only when ticket 01 resolves the runtime and boundary choices.
