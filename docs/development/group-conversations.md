# Synthetic group conversations

GramLab's simulation World can model a titled `supergroup` with explicit virtual-user and bot
memberships. This is a consumer-neutral semantic capability for scenarios that need one actor's
action to affect a different actor in a shared chat. It does not approximate a group with a private
conversation and it does not grant access to host files, credentials, or external Telegram.

## World and Bot API contract

`World.create_group_chat()` requires one non-bot creator, an explicit list of additional non-bot
members, and at least one explicit virtual bot. IDs must be positive, known, and unique across the
membership. Groups receive durable negative chat IDs; existing private Bot API chat IDs remain the
positive virtual-user IDs.

The returned group contains `id`, `type`, `title`, and memberships ordered by user ID. Supported
statuses are `creator`, `administrator`, and `member`; creation currently assigns only creator and
member. `World.get_chat_member()` returns the complete virtual user and modeled status. A member's
message is one durable event projected to every virtual-user member and queued independently for
every member bot. Bot messages and edits are visible in the same history but are not delivered to
other bots as incoming updates.

The local Bot API exposes the group envelope through existing update and send/edit methods and adds
`getChatMember`. A bot must belong to the group. Group callbacks retain the acting member, group
chat, originating bot message, and answer across World reopen. Schema 11 removes the earlier
one-recipient event and unique private-pair storage assumptions while migrating schema-10 histories,
client positions, sends, and chats atomically.

## Scenario authoring

The schema-1 control service exposes `create_group_chat` and `get_chat_member`. The typed SDK binds
the actor explicitly:

```python
owner = lab.user("Mina")
member = lab.user("Arman")
group = lab.group("Study group", creator=owner, user=member, bot="helper")
group.send("/game")
reply = group.wait_for_messages(2)[-1]
callback = reply.inline_button(0, 0).tap().callback
```

`Conversation.user` is the actor used by `send()` and simulated callback input. Handles remain
bound to one Scenario instance. Raw callers can create groups with several bots; the typed helper
currently binds one configured bot because a conversation action needs one unambiguous consumer.

The runnable [group example](../../examples/group) proves distinct creator/member identities,
`getChatMember`, real contained Bot API delivery, member-owned callback, bot edit/answer, bot
restart, post-restart delivery, exact history, lifecycle evidence, and semantic captures. In
headless Android it uses the same member binding for capture, callback and composer input.

## Headless Android projection

Bridge version 6 projects each visible supergroup to an original Telegram megagroup/channel. The
native channel ID is allocated above every user ID in that persona snapshot so Telegram never
confuses a member with the channel owner; the authenticated adapter map converts it back to the
durable negative World chat ID for every callback and send. The snapshot carries the title,
participants, visible users, history and explicit writable default permissions. Existing private
chat envelopes and their native peer path are unchanged.

The original composer may represent a group member as `inputPeerUserFromMessage`. GramLab accepts
that form only when the embedded channel is the target group, the user is the selected persona and
the referenced history message was authored by that persona. A bot-authored or cross-group
reference fails before semantic send. Group capture/input APIs likewise require an explicit member
persona; bots and unrelated users cannot act as the client.

The focused native codec serializes the complete group, decodes its writable permission record,
performs one member send and rejects a bot-authored identity reference. The public Android example
then performs a real member callback, observes the bot edit, types another member message through
the original composer, restarts the bot and cold-launches the app. Its final four-message history
and three original screenshots agree, Android reports zero accounts and both guest egress probes
remain blocked. The reviewed local APK is identified by SHA-256
`432168246376d98c3bd4eaebb791771401023946a5ef2c3f8f0c55291209c92f` and Android profile SHA-256
`fe878c649232bd571a1a64f075a79c11f5db19d30b6e3b04c9573307da83c68f`.

## Evidence boundary

Simulation proves authoritative state, membership, update envelopes, consumer behavior and restart
persistence. Headless Android additionally proves the documented projection and original-client
behavior for the pinned local build; it does not establish external Telegram service conformance,
arbitrary admin permissions, channels/topics, multiple simultaneous clients or production network
behavior. No APK is distributed by this repository.
