# Prove polling startup with an independent contained bot

Type: task
Status: ready-for-agent
Work state: integrated; focused acceptance passed, combined batch gate pending
Blocked by: none for focused acceptance

Coordinator owns `tests/fixtures/polling_startup_bot.py`,
`tests/probes/polling_startup_round_trip.py`, `tests/test_polling_startup_round_trip.py` and this
ticket. The API worker must not change these acceptance oracles.

Launch an ordinary HTTP bot in its private component after a user update is already pending.
The bot gets its identity, calls form-encoded `deleteWebhook(drop_pending_updates=true)`, polls
the now-empty queue and announces readiness through an explicit test-only pipe barrier. The
trusted scenario then creates a new Unicode message; the bot receives only that new update,
responds and acknowledges it. Preserve the original message in client history and exact next
update/message IDs. Reopen World and compare the complete HTTP transcript, unchanged pre/post
reset client snapshots, final history/events/snapshot and empty pending queue.

Demonstrate the actual current HTTP unsupported failure before integrating ticket 03. Use the
existing pinned sandbox/component and outer network guard; no client/guest or external service
is part of this core behavior. Keep capability-bearing paths out of logs. Run scoped static checks
and the integrated real-bot fixture after merge. Resolve only on observed acceptance; this proves
polling startup, not webhook delivery or complete consumer compatibility.

## Coordinator red checkpoint

The independent contained bot passes `getMe`, then receives HTTP 404 for `deleteWebhook` on the
unchanged core. The real fixture fails at that boundary in 1.22 seconds; its original JUnit and
stderr are retained in ignored artifacts. Three new source files pass scoped Ruff/format/mypy
after routine fixture formatting. Green acceptance waits for the worker branch; no guest was run.

After worker integration the independent bot fixture passes in a 38-case combined startup,
polling and Bot API selection (27.39 seconds). All complete transcript, reset snapshot, new
delivery/response, event/history and restart observations pass. The original red result remains
unchanged; the full-core batch gate is still pending.

The earlier 38-case run loaded the worker checkout through a misdirected editable install;
it is not integrated acceptance. The repaired primary import passes the complete independent
fixture in a 144-case combined feature selection (60.27 seconds). The full-core gate remains.
