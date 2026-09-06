# Android composer acknowledgment references

Reviewed 2026-09-06 against approved Android commit
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. The inspected source files match that checkout's
Git state. This original research contains no upstream implementation and proves no new runtime
behavior. No build, bot, client, account or DC interaction was performed.

## Identity and retry correlation

[UserConfig](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/UserConfig.java#L128) allocates decreasing local message IDs;
its initial counter is negative and persisted in preferences. [The send helper](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L4805)
assigns the local ID before dispatch and creates a nonzero random 64-bit `random_id` only when
one is absent. [Retries](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L4416) reuse the existing message object.
The [text request](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L5274) carries that random ID and destination peer, while the
negative local ID stays client-side. [Local insertion](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L5155) precedes dispatch and
updates both storage and the existing chat interface.

[MessagesStorage](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesStorage.java#L12745) stores the random ID alongside message ID and dialog ID.
Its [unsent loader](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesStorage.java#L8596) joins that mapping when restoring pending sends.
The [remapping operation](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesStorage.java#L13821) can resolve a missing old ID from `randoms_v2`;
normal single-send acknowledgment instead supplies the known old ID explicitly. Neither text
matching nor the local negative number is a sufficient durable world-command identity.

The current [official update documentation](https://core.telegram.org/api/updates#updatemessageid-updates)
describes deduplication by account, destination peer and random ID across sessions and method
types, without expiration. Completed duplicates return the previously generated message;
an in-flight duplicate may fail with `RANDOM_ID_DUPLICATE`. It also explains why recovering the
message alone cannot reconcile an uncertain send: `updateMessageID` restores its correlation.
Same-ID/different-payload rejection would therefore be a GramLab integrity policy requiring
explicit documentation, rather than an established equivalent server rule.

## Which response the pinned client actually consumes

[TL_updateShortSentMessage](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L48467) carries assigned ID, date, outgoing flag,
pts/count and optional entities/media/TTL. It does not carry the request random ID; the send
callback already holds the matching local message. Its serializer writes the supplied flags,
so an in-memory successful callback alone does not verify a serialization round trip.

The [single-send response handler](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L8116) accepts this compact acknowledgment,
replaces the local ID/date/entities/outgoing state, schedules difference-state processing,
and marks the message sent. Its [completion path](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/SendMessagesHelper.java#L8310) emits server-received
notifications, queues ID remapping and message storage, then emits completion notifications
again. The separate quick acknowledgment callback merely changes the visual send state; it
is not evidence that a world transaction committed.

A generic Updates response must contain a supported new-message object for this single-send
handler; otherwise it marks the send erroneous. A bare
[updateMessageID](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_update.java#L800) therefore cannot substitute
for the compact response. [Difference recovery](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesController.java#L16930) extracts ID mappings,
remaps storage and notifies the UI before processing recovered messages. The ordinary live
controller path does not expose that same standalone mapping treatment. Multi-send and forwarding
have separate response handlers; this finding does not establish their support.

## Event and acknowledgment ordering

The [chat acknowledgment handler](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java#L22332) handles a positive-ID bubble already
present by removing the old negative-ID bubble. Its
[new-message insertion](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java#L25737) also skips IDs already present.
The [storage remap](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesStorage.java#L13985) updates the old row's ID and deletes the old row when
that update fails, including a collision with an existing positive row. These are reconciliation
paths, not proof that streaming a sender's event before acknowledgment is harmless: a duplicate
can be visible until correlation arrives, and process death can interrupt reconciliation.

The send callback schedules UI work, which subsequently schedules storage work. Thus calling
the callback and then releasing an event stream is not itself a completed-storage barrier.
An adapter must either order sender acknowledgment and event application with observable
completion, or prove both orders converge without losing pending-command recovery. Identical
text from separate sends must remain distinct. Restart after world commit but before local
remapping needs durable correlation, not only snapshot history.

## pts must agree with the existing semantic bridge

The [official sequence rules](https://core.telegram.org/api/updates#pts-checking-and-applying)
compare local pts plus count with incoming pts to distinguish contiguous events, duplicates and
gaps. Private chats share one account message sequence; unrelated world journal events do not
belong to that sequence. This moving documentation supplies concepts, not a replacement for the
pinned TL constructors.

[processNewDifferenceParams](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessagesController.java#L8206) applies contiguous pts, tolerates an already-equal
value, and can queue a mismatch or request a difference. The compact acknowledgment invokes it
with seq -1, so that invocation does not advance seq/date through the seq branch. A pts value of
-1 skips pts handling internally, but that sentinel is not evidence of a faithful server response.
Zero/count-zero also depends on existing persisted pts; it is not universally safe after restart.

The existing [semantic event patch](../../clients/android/patches/0005-inline-callbacks-and-live-edits.patch)
uses `processUpdateArray` as a semantic difference and keeps the world cursor separate from
Telegram pts/seq. Adding only increasing pts to composer acknowledgments would leave other
message events outside that sequence. The implementation must reconcile this with
[ADR 0004](../adr/0004-semantic-bridge-and-world-persistence.md); this research does not select
new cursor persistence or recovery semantics.

## Narrowest seam and proof still required

The narrowest candidate is the existing request-dispatch boundary: translate the supported
`messages.sendMessage` payload to an authenticated semantic world command, and translate its
committed result to the compact acknowledgment inside the GPL adapter. Preserve the existing
composer, send helper, renderer and storage reconciliation. Unsupported flags must fail before
world mutation; plain-text success does not imply replies, scheduling, effects, media or rich
messages work. This is an implementation lead within the approved architecture, not a completed
or newly approved design.

Before calling composer support working, prove actual input causes exactly one world message and
bot update; returned positive ID/date/entities match that message; no pending negative row or
send-error bubble remains; repeated identical text produces distinct messages; and accepted retries
reuse the original result. Exercise both event/ack orders and interruption after commit, after
UI acknowledgment and before storage completion, then cold restart. Include mixed-language text,
invalid peer/capability/payload, concurrent sends, and replica catch-up while a bot replies.
Explicitly resolve persisted correlation scope, serialization flags, completion signaling,
pts translation and semantic equality with simulation mode. Retain original screenshots and
inspect storage/trace evidence; a callback invocation count cannot establish these properties.
