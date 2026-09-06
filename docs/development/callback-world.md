# Callback and edit world transitions

The shared world now supports inline callback keyboards, private bot text edits, callback delivery
and durable answers. A real independent bot receives a callback, is killed before handling it,
then restarts and edits/answers/acknowledges the same delivery. These are simulation-only and HTTP
results; the current Android patch queue still needs keyboard, callback and live edit translation.

## Reference contract and scope

The selected baseline remains Bot API 10.3, checked on 2026-09-06. Callback buttons carry
1–64 UTF-8 bytes. Queries identify the actor, originating message, data and chat instance. Clients
wait for an answer even when no notification text is needed. Stale data need not match the current
keyboard. Text edits return the edited ordinary message; answers return true. See the official
[button](https://core.telegram.org/bots/api#inlinekeyboardbutton),
[callback](https://core.telegram.org/bots/api#callbackquery),
[edit](https://core.telegram.org/bots/api#editmessagetext) and
[answer](https://core.telegram.org/bots/api#answercallbackquery) contracts.

Omitting reply markup on a text edit removes the keyboard. The official Bot API
[edit handler](https://github.com/tdlib/telegram-bot-api/blob/master/telegram-bot-api/Client.cpp)
passes the parsed markup to TDLib, including null when absent. This source observation is not an
external conformance run; error strings and limits not established by reference evidence remain
explicitly labeled prototype behavior.

Only object-form inline callback keyboards are supported. URL/game/login/Web App/reply keyboard
types, styles, custom emoji, entities and rich content still fail explicitly. Text limits count
Unicode code points; astral-character conformance remains unverified. Answers support text and a
Boolean `show_alert`, with `cache_time=0` only. URL answers, caching, expiration and re-answering an
already answered query remain unsupported. No production query lifetime is invented.

## State and delivery

`World.send_message` stores validated keyboard data with the message and its creation event.
`World.edit_message` permits only the sending bot, preserves the message ID/date, writes world
time as `edit_date`, and journals `message.edited` atomically. It replaces or removes the keyboard.
An unchanged edit fails as `MESSAGE_NOT_MODIFIED`; invalid edits leave history/events untouched.
Bot-authored edits do not become incoming bot updates.

`World.create_callback` is a persona action against its private chat and a bot-authored message.
It accepts stale data without requiring a matching current button. It creates a random query ID,
a world/chat-specific opaque `chat_instance`, an immutable originating-message snapshot, a
`callback.created` event and one bot update in the same transaction. Acknowledgment uses the
existing per-bot update offset. It never creates another chat message.

The internal `request_id` identifies a single client action. Repeating the same persona/request
ID and payload returns the original receipt and current answer, even after reopening. Reusing
that ID with another payload fails. Separate taps use distinct request IDs and create distinct
queries, including identical data. Concurrent retries are serialized and produce one update.
This is the owned bridge's retry contract, not an extra Bot API parameter or a Telegram wire claim.

Only the originating bot can answer a query. The answer and `callback.answered` event persist
together. Only the requesting persona can read that answer. Storage version 3 adds the callback
ledger; versions 1 and 2 migrate without replacing world identity, messages or pending updates.
The ledger currently has no pruning or expiry policy.

## Client HTTP commands

Use the same generated bearer capability and independently contained service as the
[client read boundary](client-bridge.md).

| Request | Body/result |
| --- | --- |
| `POST /v1/callbacks` | Exactly `request_id`, `chat_id`, `message_id`, `data`; returns the persisted callback receipt |
| `GET /v1/callbacks/{id}` | Returns that persona's receipt and nullable `answer` |

Responses contain `schema: 1`, `world_id`, `user_id` and `callback`. The callback includes `id`,
`user_id`, `chat_id`, `message`, `data`, `chat_instance` and `answer`. Answer objects contain `text`,
`show_alert` and `cache_time`. The persona comes exclusively from authentication. POST requires
bounded UTF-8 JSON with one Content-Length; duplicate members, extra/query fields and malformed
IDs/data fail before mutation. Bot/world capabilities cannot impersonate a client. The existing
event endpoint filters callback events to their actor and edit events to their conversation.

## Evidence and remaining work

The keyboard regression first returned unsupported parameters, edits returned unsupported methods,
and the missing callback transition and HTTP route failed explicitly. Focused checks now cover
full HTTP messages, byte limits, wrong senders/actors/worlds, stale data, concurrent retry identity,
durable answers and concurrent prior-format migration.

The independent [callback bot](../../tests/fixtures/callback_bot.py) imports no GramLab code.
The contained [recovery probe](../../tests/probes/callback_round_trip.py) exchanges actual HTTP,
waits for callback receipt, sends SIGKILL, and starts a new bot process. The callback remains
pending and is replayed; the restarted bot edits the same message, answers, then acknowledges.
The test checks the exact final history, API edit/answer responses, replayed query ID, process
termination and empty outbox. Synthetic transcripts are scanned for capabilities and remain
ignored. This proves interruption before mutation; interruption after an edit/answer but before
acknowledgment still needs a separate recovery policy and test.

The full core gate passes 34 tests with 91.47% statement coverage. All seven existing Android
tests also pass against storage version 3, preserving the earlier plain-text startup proof.
Python static, Nix/direnv/workflow, local-link and public-tree privacy checks pass. Use the
[documented outer network guard](runtime-boundary.md) and `pytest -m 'not android'` for that gate.
The subsequent [Android interaction loop](android-callbacks.md) proves actual tapping and visible
editing. Bot launches now use [private component filesystems](component-boundary.md), including
persistent bot state across the controlled kill/restart. Broader update ordering/replica recovery,
resource limits and the full compatibility inventory remain active work.
