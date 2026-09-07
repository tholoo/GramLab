# Support standard polling startup and explicit pending-update discard

Type: feature
Status: implementation
Work state: claimed on `task/polling-startup-reset`; implementation complete, awaiting integration
Blocked by: none; polling-only scope and shared contract frozen below

A normal bot may call `deleteWebhook(drop_pending_updates=True)` before `getUpdates`. GramLab
currently returns an unsupported-method error, so the process cannot reach its message handlers.
Implement this existing Bot API operation against the current polling-only World. The lack of a
configured webhook is real state, not a reason to invent a network route or claim webhook delivery.

## Frozen contract and ownership

Worker owns `src/gramlab/world.py`, `src/gramlab/bot_api.py`, a new
`tests/test_polling_startup.py`, and this ticket on `task/polling-startup-reset`. Coordinator owns
other fixtures, shared docs, full gates and integration. Add a public World queue-discard operation
using the existing SQLite writer boundary; helper naming is routine worker choice. No schema,
Android, dependency, renderer, network or webhook-registration change is assigned.

- `deleteWebhook` accepts only optional `drop_pending_updates` under existing strict parameter
  validation and returns the complete usual HTTP success envelope with Boolean true. A currently
  absent webhook remains absent. Repetition succeeds; omission/false preserves pending updates.
- True discards only the authenticated bot's currently queued deliveries atomically. Keep
  messages, callbacks/answers, events, client snapshots, next update IDs, subscriptions and other
  bots/worlds unchanged. Subsequent arrivals remain deliverable, including after server/World
  restart; this operation is distinct from deleting messages or resetting a World.
- JSON Boolean and form/query textual input follow the existing supported transport shapes.
  The pinned textual decoder lowercases/trims and recognizes `true`, `yes`, `1`; other text is
  false. Resolve JSON non-Boolean handling explicitly from source or preserve a documented strict
  typed boundary; do not use Python truthiness to turn arbitrary objects into deletion.
- Deleting an absent webhook must not manufacture a same-bot long-poll conflict. Preserve an
  already waiting empty poll and prove a later arrival still completes it normally.
- Wrong capability, malformed requests, repeated members/parameters and unsupported fields fail
  before queue/state mutation. World operations reject non-bot identities.
- `setWebhook` and webhook delivery remain explicitly unsupported. Do not return generic success
  for either or route any request externally. Existing polling semantics stay unchanged.

## Independent source basis

Pinned Bot API server [dispatch and deletion path](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L16952-L17024)
uses an empty URL for deletion and aborts long polling only for a nonempty new URL. The
[queue-clear and Boolean decoder](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L10044-L10056)
and [completion](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L17227-L17285)
establish drop and success behavior. TDLib's [queue clear](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tddb/td/db/TQueue.cpp#L206-L274)
removes queued contents without resetting the queue tail. These are reference observations,
not a source import, server run or complete webhook-conformance claim.

## Acceptance and verification

Demonstrate the current unsupported failure through actual HTTP before implementing. Compare
complete HTTP updates/responses, persistent queues, history/events, callbacks and client snapshots
through public World operations. Cover true/false/omitted and repeated reset, real HTTP JSON/form/
query encodings, cross-bot/World protection, new-arrival IDs, persisted selection, restart and the
waiting-poll case with an observed test scheduling barrier rather than timing guesses. Rejected
requests must preserve full state. Keep queue-drop ordering separate from a broad concurrency claim.

Run the new file plus existing update delivery/polling/Bot API tests in the assigned pinned shell
and outer network guard; retain distinct red/green JUnit/logs. Run scoped Ruff/format and source
mypy. No guest or full gate is assigned. Commit only owned files; return a frozen clean branch,
precise observed limits and terminal resources. Leave the ticket claimed until coordinator review
and integrated acceptance. Consumer source/code/names/configuration must remain out of this public
repository; use independently authored generic fixtures.

## Worker evidence

- Three pre-implementation HTTP cases against an immutable copy of the assigned base returned
  unsupported-method 404 instead of success; `/tmp/polling-startup-http-red.xml` retains that red
  run. The public World method was absent as well.
- The final focused suite passes 19 cases under the loopback-only outer network guard;
  `/tmp/polling-startup-focused-final.xml` retains the result.
- The new tests plus `test_update_delivery.py`, `test_polling.py` and `test_bot_api.py` pass 63
  cases together under the same guard; `/tmp/polling-startup-regression.xml` retains the result.
- Scoped Ruff check/format and mypy pass. These checks establish only the polling startup reset
  contract; webhook registration/delivery, an external bot and Android were not exercised.
