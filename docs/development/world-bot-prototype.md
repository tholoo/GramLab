# Persistent world and real local bot prototype

Status: an independently implemented SQLite world and a real local HTTP bot exchange work in
network containment. This is the internal foundation for the approved Android bridge, not the
public simulator SDK or a completed Telegram compatibility profile. [Synthetic Android startup](android-application.md)
renders the plain-text exchange. [Callback/edit transitions](callback-world.md) now have separate
HTTP and real-bot recovery evidence; Android translation of those additions is pending.

## Implemented behavior

[`World`](../../src/gramlab/world.py) creates a new dedicated directory, preserves virtual users,
private user–bot chats, world time and seed metadata, and refuses to overwrite an existing world.
Message history, ordered semantic events and bot updates are written in one SQLite transaction.
Four concurrent writers retain a single message/event/update order. IDs are local to their world;
private chat IDs exposed to a bot are the virtual user's ID, while internal conversation IDs are
mapped separately. Reopening a world preserves history, IDs and acknowledged delivery state.

Reading updates without a newer offset repeats unacknowledged delivery. A higher offset confirms
older updates for that bot only. Bot replies enter the same world history and event journal;
they do not echo back into that bot's incoming-message queue. Invalid actors/text do not consume
message IDs, journal positions or update IDs. Time advances explicitly and cannot move backwards.
The seed is currently persisted metadata; randomized scenario/fault scheduling is not implemented.

Only generated `gramlab_` capabilities authenticate bots. Their hashes are persisted, their values
are independent of the scenario seed, and another world's token is rejected even when numeric bot
IDs match. Request paths containing capabilities are excluded from access logs. A bot cannot send
into another bot's private conversation through this API.

[`BotAPIServer`](../../src/gramlab/bot_api.py) binds an ephemeral loopback port and defensively
requires a loopback-only interface list. The authoritative isolation mechanism is still the
[process boundary](runtime-boundary.md); that interface check alone is not a sandbox.

| Current HTTP subset | Evidence and limits |
| --- | --- |
| `getMe` | Locally issued capability returns the virtual bot identity; wrong-world/malformed tokens fail |
| `getUpdates` | Pending messages, positive offsets and limits 1–100; negative offsets, long polling and filters remain explicitly unsupported |
| `sendMessage` | Plain text and callback-only inline keyboards in existing private chats |
| `editMessageText` | Sending bot edits its text/keyboard atomically; returns the persisted message |
| `answerCallbackQuery` | Durable answer to its own query; text/alert with caching disabled |
| Transport | Case-insensitive methods, GET query parameters and POST JSON; other content types are explicitly unsupported |
| Rejection | Unknown methods/parameters, wrong bot, duplicate JSON fields and oversized integer identifiers fail without state changes |

The baseline is [Bot API 10.3](https://core.telegram.org/bots/api). Identity/message shapes and
polling acknowledgment follow its documented contracts. This is local evidence for the listed
subset, not external conformance. Plain-text validation currently counts Unicode code points for
the documented 1–4096-character limit; astral-character boundary conformance remains unverified.
Formatting/entities, automatic command/link recognition, other keyboard types, webhooks,
media and other API methods remain open work. Unknown operations receive explicit errors.

## Real-process evidence

[`echo_bot.py`](../../tests/fixtures/echo_bot.py) is a separate Python process with no GramLab
implementation imports. It receives only its generated local token and explicit loopback endpoint,
calls `getMe`/`getUpdates`, replies through `sendMessage`, and acknowledges the received update.
The test compares the full HTTP results and persisted world history for mixed Persian/English
text. The client does not use proxy discovery or follow redirects. It and the server run inside
the independent process boundary, with no external route or inherited operator configuration.

Run the applicable core gate after provisioning, inside the additional network guard:

```sh
nix develop
unshare --user --map-root-user --net bash -eu <<'BASH'
ip link set lo up
.venv/bin/pytest -m 'not android' --cov=src/gramlab --cov-report=term-missing --cov-fail-under=80
BASH
```

Select a fresh ignored `--basetemp=artifacts/<run-id>` to retain the bot's `round-trip.json` and
synthetic databases. Pytest deletes an existing base directory, so never reuse needed artifacts.
Host-specific observations and process handles belong in ignored local notes.

Verification on 2026-09-06: all 22 core tests pass with 89.79% statement coverage; four unchanged
Android-dependent tests are excluded from this gate. Strict typing, lint/format, Nix/workflow,
local links and the public-tree privacy scan pass. Regressions exposed missing participant/text
validation, duplicate JSON acceptance, oversized ID crashes and invalid polling options consuming
updates; each was reproduced before its correction. The manually dispatched CI was not run remotely.

## Remaining foundation gates

The current trusted bot fixture shares its run's data mount with the supervisor. Separate bot
filesystem permissions, private component mounts and resource limits are not established yet;
HTTP capability checks do not protect a database from code that can directly write that file.
There is no public launcher or client control endpoint yet. The authenticated
[semantic client read boundary](client-bridge.md) now supplies persona-scoped snapshots and events.

The legacy participant snapshot and history/event reads remain separate operations; Android must
use the new transactional client snapshot/cursor. Abrupt process interruption
at delivery boundaries, actual bot/client restart reconciliation, TTL/fault behavior and replay
remain work. The successful database reopen tests do not substitute for those cases.

Next connect the approved native/startup guards and Java-side semantic translation, preserve
actual Android rendering, and complete the real tap/callback/edit/restart loop. Do not enable the
preparation APK before the required application-specific network and identity changes.
