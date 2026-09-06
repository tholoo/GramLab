# Update delivery references

Reviewed 2026-09-06 for the existing Bot API 10.3 baseline. This is original contract research,
not upstream implementation or evidence of running the official server. No bot, account,
Android client or Telegram DC was used.

## Reproducible source boundary

The official [version commit](https://github.com/tdlib/telegram-bot-api/commit/2efabc722e9493b9cac450233198d09e5cea0573)
is `2efabc722e9493b9cac450233198d09e5cea0573` (10.3). Its
[Git tree](https://api.github.com/repos/tdlib/telegram-bot-api/git/trees/2efabc722e9493b9cac450233198d09e5cea0573)
pins TDLib to `bc9c263e2bfee06aaab41e82db51a103376030bc`. Use these immutable revisions.
The [public documentation](https://core.telegram.org/bots/api#recent-changes) is moving and
currently identifies 10.3. This research does not change GramLab's Android or API baseline.

## Public delivery contract

`allowed_updates` selects future delivery types; previously created updates can still arrive.
Omission retains the previous selection. An empty array restores the default, which excludes
`chat_member`, `message_reaction` and `message_reaction_count`. The complete public name inventory
is the optional fields of [Update](https://core.telegram.org/bots/api#update), including
`guest_message`, `subscription` and `stopped_message_generation`.
[getUpdates](https://core.telegram.org/bots/api#getupdates) returns earliest unconfirmed updates
by default; a higher offset confirms earlier identifiers. A negative offset selects a suffix
and forgets its predecessors. Limits are 1–100, default 100. A positive timeout waits for
updates. These documentation promises alone do not specify malformed-filter handling or exact
concurrent-poll ordering. Accepting a subscription name does not imply GramLab can generate it.

## Source-level qualifications

The pinned [parser](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L18310)
lowercases strings, ignores unknown names and collapses duplicates. Empty/all-unknown arrays
restore defaults. Omission, empty parameter text, malformed JSON, non-arrays or any non-string
array element leave the selection unchanged, without rejecting the poll. Recognized names include
undocumented `custom_event` and `custom_query`.
[Filtering](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L18387)
precedes queue insertion: excluded events consume no update IDs.

[Request processing](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L16926)
checks webhook conflict, parses/clamps integers, changes selection, then reads/forgets updates.
Malformed filters still permit acknowledgment. An earlier poll receives 409 only when the new
request enters an empty-result wait; an immediate response does not universally interrupt it.
[Waiting](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L17588)
normalizes negative offsets once, preserves positive offsets, and reuses that offset on wake.
Queue-read errors fall back to the current head. Repeated-call throttling can alter timeout/limit.
Selection is saved/restored through `xallowed_update_types`.
[Option handling](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L9811)
confirms the restore path.

The [default mask and type inventory](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.h#L1510)
include both custom types, while excluding the three opt-in public types from defaults.
[TDLib options](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/OptionManager.cpp#L54)
load the persisted configuration and emit option updates; their
[write path](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/OptionManager.cpp#L388)
persists changes. This supports restart persistence, but does not establish a crash-durability
barrier at the HTTP response.

## Queue consequences

Pinned [TQueue.clear](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tddb/td/db/TQueue.cpp#L221)
keeps the last N queued events by count, not identifier subtraction. If fewer than N exist,
nothing is dropped. Thus with five queued events, offset -3 and limit 1 retains the last three
and returns the earliest retained event; the other two remain pending. A negative poll beginning
empty must not repeatedly trim later arrivals while waiting.

[TQueue.get](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tddb/td/db/TQueue.cpp#L295)
rejects offsets more than ten above its tail (the next identifier), or extremely far below its
head. Within that future window,
[reads](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/tddb/td/db/TQueue.cpp#L432)
forget events below the requested offset. Together with the waiting behavior above, a positive
future offset can discard later arrivals below it. Beyond the window, fallback can return
older queued events instead. Therefore neither universally normalizing positive offsets nor
universally deleting all lower IDs reproduces the inspected source. This distinction is an
inference from both functions, not live-server conformance evidence.

## GramLab implementation guidance and limits

Test pending rows across filter changes, omitted filters after restart, reset behavior, recognized
but unimplemented subscriptions, malformed filters with acknowledgments, count-based suffixes,
and empty negative long polls with multiple later arrivals. Keep delivery filtering separate from
authoritative chat history and client events. Report integer validation, poll replacement,
future-offset fallback and flood-timing differences explicitly if existing bounded policies remain.
Do not claim exact server compatibility from the documentation alone. HTTP framing errors,
crash recovery timing, expiry and webhook coordination require their own evidence.
