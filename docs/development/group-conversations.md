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
restart, post-restart delivery, exact history, lifecycle evidence, and semantic captures.

## Evidence boundary

This capability is simulation-only. It proves authoritative state, membership, update envelopes,
consumer behavior, restart persistence, and semantic captures. The current Android client bridge
still projects private chats only, so headless Android group runs reject rather than silently
substituting a private chat. No screenshot, native input, or external Telegram conformance claim
follows from the simulation example.
