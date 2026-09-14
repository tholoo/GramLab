# Interactive Android playground

Status: resolved

## Problem

The persistent playground exposes either command-driven headless Android or a browser-built chat
facsimile. A person cannot open the actual Telegram Android client, click its composer, type,
send, or use its rendered controls. The browser client is the wrong fidelity boundary for this
workflow.

## Contract

- `interactive-android` runs the same original, reviewed Telegram Android client and authoritative
  World as headless Android, but exposes a visible emulator window.
- The display connection is opt-in, local, minimal, and does not weaken the run's loopback-only
  network, private filesystems, synthetic identities, or zero-account boundary.
- The native composer and rendered rich buttons drive the real local consumer and resulting World
  changes; reset restores the exact seeded World and returns the visible client to coherent state.
- Simulation and headless Android remain available for automation. A browser facsimile is not the
  default human playground and supplies no Telegram fidelity evidence.
- Unsupported native Telegram administration flows are stated precisely; host control operations
  do not masquerade as native interaction.

## Acceptance

- A red-first public runner test rejects `interactive-android` before implementation and accepts it
  afterward with the reviewed Android inputs and an explicit display connection.
- Focused isolation tests prove only the selected display socket is mounted while ambient display
  paths and unrelated host runtime files remain hidden.
- A serialized native playground run shows a mapped emulator window, sends text through the
  original composer, taps an original rich button, observes real consumer effects, resets exact
  state, and retains screenshots plus blocked IPv4/IPv6 evidence.
- Documentation distinguishes verified native interaction from any remaining unsupported native
  membership-management flow.

## Resolution

Resolved on 2026-09-14. `interactive-android` keeps QEMU headless and opens its actual guest display
through a contained scrcpy component. The runner accepts one explicit Unix display socket, mounts it
at a fixed private path, and rejects missing viewer tooling or non-socket display paths. Focused
tests prove neighboring host sockets and ambient host paths remain invisible.

A serialized generic consumer run opened the mapped viewer and retained blocked guest IPv4/IPv6
evidence. A downstream consumer acceptance then displayed the actual Telegram client, sent a command
through its native composer, observed the real bot response, restored the exact seeded state, and
stopped with a passing result. Its setup also exercised an original rendered rich-button callback.
Direct window interaction is supported; native member-picker administration remains outside the
contract, and the authenticated `add-bot` control is documented as a World transition.
