# Durable client text commands

Status: the independent world/HTTP boundary passes focused loss, retry, concurrency, isolation
and migration tests. Native composer integration and its recovery gates remain in progress in
[ticket 04](../../.scratch/programmatic-scenarios/issues/04-native-composer.md). Python evidence
does not establish Android input, acknowledgment or rendering fidelity.

The existing [client capability](client-bridge.md) selects the non-bot persona. Version 2 uses
the same isolated local service and authorization; callers cannot supply another sender.
Existing version 1 reads and callback commands retain their previous shapes.

| Request | Result |
| --- | --- |
| `POST /v2/messages` | `schema`, `world_id`, `user_id`, `send` |
| `GET /v2/snapshot` | The version 1 snapshot fields plus `message_position` and `sends`, with schema 2 |
| `GET /v2/changes?after=N&limit=L` | `schema`, `world_id`, `user_id`, `cursor`, `head`, `now`, `changes` |

A text command requires `request_id`, `chat_id` and `text`, with optional supported formatting
`entities`. The request ID is a 1–128 character ASCII identifier using letters, digits, underscore
or hyphen. Text and UTF-16 entity ranges use the existing [formatting contract](formatted-text.md).
The HTTP body is bounded to 64 KiB; duplicate, missing and extra fields fail before mutation.

`send` contains the accepted `request_id`, its persona message `position` and the immutable
created `message`. One SQLite writer transaction validates the persona/destination and commits
the message, journal event, eligible bot outbox entry, message position and send receipt. Retrying
the same persona/destination/request ID with the same normalized payload returns that exact
receipt, including its original date and position, after a lost response or service restart.
An equal text with a new request ID is a separate message. Other personas and destinations have
independent request namespaces. Changed payload with the same ID is rejected: this is GramLab's
integrity policy, not a claim of equivalent Telegram server behavior.

Message positions count only message creation and editing visible to that persona, across its
supported private conversations. Clock, callback, bot subscription and other personas' events
do not consume these positions. Each change contains `position`, `type` and the original `data`;
a client-created message additionally carries `request_id`. The journal cursor remains a separate
field with its existing meaning. Neither is exposed as an upstream TL object in Python.

Changes are contiguous after the requested position. `limit` defaults to 100 and accepts 1–1000;
`cursor` is the last returned position and `head` is the message position observed in the same
read transaction. A future position fails. Snapshot history, journal cursor, message position
and all send receipts are likewise read atomically. There is no message-change retention limit
or send-receipt expiry in this experimental implementation.

World storage version 5 adds message positions and send receipts. The version 4 migration
backfills creation/editing positions from the ordered journal in one transaction, preserving
identities, capability hashes, messages, callbacks, subscription filters and pending bot updates.
Concurrent openers recheck the storage version after obtaining the writer lock.

## Verification

Run [the boundary tests](../../tests/test_client_sends.py) with the existing client/world/callback
and update-delivery regressions inside the documented offline runtime. They exercise actual HTTP
response loss after commit, concurrent retries, cross-persona and cross-destination isolation,
formatted sends, changed-payload rejection, atomic snapshots and concurrent migration from the
standalone version 4 fixture. Seven initial failures established the missing contract; all
53 focused tests pass. The subsequent full core gate passes 186 tests at 82.55% coverage.

The [Android acknowledgment](android-composer-references.md) and
[Unicode input](android-input-tooling-references.md) references guide the separately licensed
adapter work. Its actual Send button, persistent client database, sequence handling and recovery
remain separate acceptance requirements. No external account/DC conformance was performed.
