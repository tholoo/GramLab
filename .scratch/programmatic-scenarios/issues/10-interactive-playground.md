# Keep an isolated Android world open for interactive review

Type: task
Status: ready-for-agent
Work state: resolved
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
- An authenticated playground action adds a selected configured bot to a named seeded group on
  behalf of its creator. The group must initially exclude that bot, the action must enqueue the
  ordinary `my_chat_member` update, and the running consumer must be able to answer in that group.
- Reset stops consumer processes, restores both World and consumer files to the exact post-setup
  baseline, refreshes the Android client from that baseline and restarts consumers without changing
  run identity or allowing an old process to write afterward.
- Stop terminates every owned descendant and emulator, preserves a redacted report, and is
  idempotent. Start refuses a second owner for the same playground.
- Missing, stale and mismatched control capabilities fail without changing another playground.
- Simulation mode proves start/add-bot/reset/add-bot/stop and exact baseline equivalence at public
  process, HTTP and persisted-state seams. Android acceptance proves the kept-open original client
  is usable, membership refresh is visible, reset returns its visible chat list/history to baseline,
  and guest IPv4/IPv6 egress remains blocked.
- Documentation exposes a small consumer-neutral interface and records that simulation is semantic
  evidence while only Android establishes interactive rendering fidelity.

## Public seams

Tests use the public CLI/runner, authenticated scenario interface, consumer process behavior,
versioned client snapshot and original Android runner. Private World helpers, direct database
mutation and UI injection are not acceptance seams.

## Comments

Approved by the user on 2026-09-14 for an offline consumer development playground with a seeded
operations group, a group containing the target bot, a group excluding it, and fast baseline reset.
The reusable lifecycle and reset implementation remains consumer-neutral; each consumer owns its
separate setup adapter.

Claimed on 2026-09-14 on `task/interactive-playground`. The first implementation slice owns the
generic persistent runner/controller and simulation reset contract; Android execution follows the
same interface after the lifecycle seam is proven without a guest.

Resolved on 2026-09-14. The public simulation acceptance drives a real consumer message, rich
callback/edit, creator-authorized bot addition, ordinary `my_chat_member` delivery, consumer reply,
reset and repeated bot addition. It also proves exact authoritative World restoration, consumer-file
restoration, detached-descendant containment, capability rejection, deep output-path control and
idempotent stop. Sixty-four rejected label lookups followed by a valid tap prove that misses do not
consume the interaction budget.

The serialized Android acceptance passed against patch-35 APK SHA-256
`fff0c33f6991202b08a63e77a501f3bc188eecda9ae45047bf1cf39400c11521`: the original client rendered
the added membership/reply, reset returned the open chat to its empty baseline, both PNG captures
were asserted and guest IPv4/IPv6 remained blocked. The final contained non-Android gate passed all
1,625 tests at 85.11% coverage. JUnit SHA-256:
`0e2043f13346026605dc861daffa17497f88e383548f1d86822caa3a7920618c`. Repository Ruff lint and
format checks and maintained strict typing scopes pass. Publication remains subject to explicit
remote approval.
