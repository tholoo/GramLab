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
group.type("/game")
reply = group.wait_for_messages(2)[-1]
observed = lab.rich_buttons(chat_id=group.id, message_id=reply.id, user_id=member.id)
target = next(item for item in observed["targets"] if item["label"] == "Continue")
callback = lab.tap_rich_button(target_id=target["target_id"])["effect"]["callback"]
```

`Conversation.user` is the actor used by `send()`, `type()` and simulated callback input. Handles remain
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
persona; bots and unrelated users cannot act as the client. Rich-button observation similarly
requires an explicit non-bot member and retains that actor with the group's signed chat ID through
the native arm, original touch, callback correlation and durable receipt.

The focused native codec serializes the complete group, decodes its writable permission record,
performs one member send and rejects a bot-authored identity reference. The public Android example
then observes and taps an actual rich button as the selected member, correlates callback actor `3`
and durable chat `-1`, observes the bot edit, restarts the bot, types another member message through
the original composer and cold-launches the app. Its final four-message history and three inspected
original screenshots agree, Android reports zero accounts and both guest egress probes remain
blocked. The 110.19-second retained run is under `artifacts/group-rich-native-05/`; its result
SHA-256 is `910176a564bbdbdda4ae09b5cabb006b612ca2d156ebb94f3ffc542246bdb3ab`.
The reviewed local 35-patch APK is identified by SHA-256
`fff0c33f6991202b08a63e77a501f3bc188eecda9ae45047bf1cf39400c11521` and Android profile SHA-256
`fe878c649232bd571a1a64f075a79c11f5db19d30b6e3b04c9573307da83c68f`.

Two preceding attempts timed out before scenario startup at the former 120-second guest-boot cap;
a third booted after 159.34 seconds but hit the separate 40-second first-client-draw cap. The runner
now allows at most 180 seconds for boot and 90 seconds for `am start -W`, each still bounded by the
manifest deadline. The passing run booted in 55.63 seconds. These retained failures document why
the timing correction exists; they are not counted as feature evidence.

## Evidence boundary

Simulation proves authoritative state, membership, update envelopes, consumer behavior and restart
persistence. Headless Android additionally proves the documented projection and original-client
behavior for the pinned local build; it does not establish external Telegram service conformance,
arbitrary admin permissions, channels/topics, multiple simultaneous clients or production network
behavior. No APK is distributed by this repository.
