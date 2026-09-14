# Keep an isolated Android world open for interactive review

Type: task
Status: ready-for-agent
Work state: open
Blocked by: 09-group-rich-input.md

Add a generic persistent interactive mode to the public GramLab runner. Consumer repositories may
describe their own synthetic world and bot configuration, but GramLab must own lifecycle, reset,
containment, Android projection and cleanup without knowing the consumer application's domain.

## Acceptance

- A public command starts one offline isolated World, selected local bot processes and the original
  Telegram Android client, then keeps them available for human interaction until explicitly stopped.
- A manifest-owned setup hook creates synthetic users, private chats and groups, including groups
  whose membership deliberately excludes a selected bot; setup uses public scenario operations,
  never direct World database writes.
- Reset stops consumer processes, restores both World and consumer files to the exact post-setup
  baseline, refreshes the Android client from that baseline and restarts consumers without changing
  run identity or allowing an old process to write afterward.
- Stop terminates every owned descendant and emulator, preserves a redacted report, and is
  idempotent. Start refuses a second owner for the same playground.
- Missing, stale and mismatched control capabilities fail without changing another playground.
- Simulation mode proves start/reset/stop and exact baseline equivalence at public process, HTTP and
  persisted-state seams. Android acceptance proves the kept-open original client is usable, reset
  returns its visible chat list/history to baseline, and guest IPv4/IPv6 egress remains blocked.
- Documentation exposes a small consumer-neutral interface and records that simulation is semantic
  evidence while only Android establishes interactive rendering fidelity.

## Public seams

Tests use the public CLI/runner, authenticated scenario interface, consumer process behavior,
versioned client snapshot and original Android runner. Private World helpers, direct database
mutation and UI injection are not acceptance seams.

## Comments

Approved by the user on 2026-09-14 for an offline Mostly Play development playground with a seeded
admin-log group, a group containing the bot, a group excluding the bot, and fast baseline reset.
The reusable lifecycle and reset implementation remains consumer-neutral; Mostly Play owns its
separate setup adapter.
