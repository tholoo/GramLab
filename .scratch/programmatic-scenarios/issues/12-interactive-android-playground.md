# Interactive Android playground

Status: claimed

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
