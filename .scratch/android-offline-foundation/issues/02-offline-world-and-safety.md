# Establish isolated synthetic state and enforce offline execution

Type: task
Status: ready-for-agent
Work state: claimed
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

2026-09-05: Claimed after the user approved ticket 01's proposal. Reproducible development
provisioning is underway; next prove the independent runtime boundary and synthetic startup.
No client/bot execution is authorized without the required containment.

Preparation completed: pinned Nix core/Android shells, optional direnv Android selection, local
cache paths, formatter/checks and manually dispatched CI. Core/direnv entry, SDK package
realization, network-isolated Android tool version checks, source/submodule pins and archive
checksums passed. The SDK's duplicate legacy NDK alias was removed and rechecked. Actual world
state, OS containment runner, synthetic Android activation and the interaction loop are still
unimplemented. Keep host-specific records in ignored local notes, as requested by the user.

2026-09-06: Implemented the experimental Linux process boundary and Python packaging on
`feat/offline-runtime-boundary`. Nine real-process tests pass with 90.10% coverage; typing,
lint/format, Nix/direnv/workflow checks, configuration parsing and local links pass. Regression
tests caught symlinked data-root acceptance and premature timeout cleanup; both are fixed.
The [runtime evidence](../../../docs/development/runtime-boundary.md) records exact capabilities,
portable commands and remaining limits. No Android guest/client or real bot has started; world
state and the acceptance criteria above remain open. The manual CI now requires the runtime gate
but has not been dispatched remotely. Next extend the provisioned profile and validate dedicated
Android guest startup/egress before synthetic activation.
