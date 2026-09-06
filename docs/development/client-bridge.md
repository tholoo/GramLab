# Semantic client boundary

Status: the Python side of the approved Android bridge has authenticated HTTP reads and
transactionally consistent snapshots. The [Java snapshot adapter](android-semantic-bridge.md)
translates plain-text snapshots into the actual Android application. The server now adds
[callback commands and edits](callback-world.md); their Android translation is still pending.
This protocol is independently owned; upstream TL objects belong in the separately licensed
Android adapter, not the MIT core.

## Identity and transport

The trusted supervisor starts [`ClientBridge`](../../src/gramlab/client_bridge.py) with one world
directory inside the [process boundary](runtime-boundary.md). It binds an ephemeral loopback port.
Its interface-list check is defensive and does not replace OS containment. The emulator reaches
that service through its local host alias; production hosts and external fallback are forbidden.

`World.issue_client_token(user_id)` creates a random `gramlab-client_` capability for a non-bot
persona. Send it in the `Authorization: Bearer …` header. Only its SHA-256 hash persists, independently
of the scenario seed. Bot capabilities and another world's client capabilities are rejected even
when numeric user IDs match. The service derives the persona from the capability; a query cannot
select another user. Responses are marked `Cache-Control: no-store`, and raw request logging is
disabled. Capabilities must stay out of reports, URLs and screenshots.

| Request | Result |
| --- | --- |
| `GET /v1/snapshot` | `schema`, `world_id`, `user_id`, `cursor`, `now`, `users`, `chats`, `messages` |
| `GET /v1/events?after=N&limit=L` | `schema`, `world_id`, `user_id`, `cursor`, `head`, `events` |

Schema is currently `1`. Unknown routes return 404; missing/invalid capabilities return 401;
unsupported, repeated or invalid query parameters return 400. Errors contain
`{"schema":1,"error":{"code":"…","message":"…"}}`. Callback command routes are defined in the [callback protocol](callback-world.md). Client
message submission, media transport and general control operations remain unimplemented.

## Snapshot and cursor contract

The snapshot contains the persona, its private-chat bots, its conversations and their messages.
It excludes other personas and their conversations. One SQLite read transaction supplies all
fields, including the journal cursor, so a concurrent message cannot appear without its cursor
or move the cursor ahead of the returned history. Users/chats are ordered by ID; messages are
ordered by conversation ID then message ID. IDs retain the internal semantic-world meaning
described in the [world prototype](world-bot-prototype.md).

Persist `world_id`, persona and applied cursor together on the client. `world_id` is a random,
persistent identity, independent of the seed. A different world or persona requires discarding
the previous client projection and taking a new snapshot. Opening the prior version-1 database
migrates it transactionally through storage version 2 to version 3. Version-2 worlds retain their
identity when gaining the callback ledger; history and pending bot delivery are preserved.
Wire schema versions and SQLite storage versions are separate.

An event request scans at most `limit` journal entries (default 100, range 1–1000) strictly after
the requested cursor. It returns only entries visible to the persona. Hidden entries advance the
returned cursor, so gaps and empty batches are valid. `head` is the global journal head in the
same read transaction. Continue from the returned cursor until it equals `head`; never calculate
the next cursor from the number of visible events. The global positions reveal journal activity
counts, but no other persona's event payload. They are not Telegram `pts` values.

Current event types are `user.created`, `chat.created`, `message.created`, `message.edited`,
`clock.advanced`, `callback.created` and `callback.answered`.
Each has `sequence`, `type` and semantic `data`. An unknown type fails explicitly. A new chat can
refer to a bot created before the client's snapshot; the adapter must resnapshot when a referenced
participant is missing. Negative/future cursors are rejected; future cursors require resnapshot.
The journal currently has no pruning, retention policy or long polling.

## Evidence and limits

[`test_client_bridge.py`](../../tests/test_client_bridge.py) checks complete persona snapshots,
identity persistence, previous-format migration with pending delivery, filtered cursor progression,
concurrent message writes, actual HTTP authentication and invalid requests. The service is stopped
and reopened with the same world and capability. Run these tests with the documented outer network
guard, alongside the full core gate. These are server-side contract tests, not Android UI evidence.
The expanded 2026-09-06 core gate passes 34 tests with 91.47% statement coverage; Android coverage is separate.

Snapshots currently include full history and have no pagination or resource quotas. Real bot
fixtures now have [private component filesystems](component-boundary.md), while world services
and emulator orchestration remain trusted. A bot killed before callback handling can restart and complete
delivery. The [Android callback loop](android-callbacks.md) now demonstrates actual tapping, live
Java message edits and recovery of the latest edited message after client restart. Recovery after
partial mutations, atomic local projection/cursor transactions, older cached-message reconciliation
and live participant changes remain foundation gates.
