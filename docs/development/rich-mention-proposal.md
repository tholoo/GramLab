# Proposed explicit rich-user mentions

Status: proposal for consultation; identity disclosure and bridge changes are not approved.

Support a bot mentioning a known synthetic user in recursive rich text, including a user outside
the recipient's conversation. Store the referenced ID in the World, return authoritative User
objects at the Bot API boundary, and deliver identity dependencies before the original Android
renderer applies the message. This keeps explicit named-user mentions separate from automatic
`@username` detection and profile navigation.

## Pinned contract and current gap

The Bot API accepts `{"type":"text_mention","text":<RichText>,"user":{"id":<ID>}}`.
Its decoder reads `user.id` and ignores the remaining supplied User fields
([input](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12175-L12181)).
Output includes an authoritative complete User object rather than echoing those input fields
([output](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L808-L813)).
Consequently, accepting only an `id` field and rejecting a returned full User would unnecessarily
break output-to-input round trips. Accept the supplied User object, consume only its validated ID,
and discard other identity claims under the existing duplicate-member/depth/size limits.

TDLib recursively converts the label and resolves the ID through `get_input_user`; syntax alone
does not establish access
([validation](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L266-L274)).
Referenced user IDs are message dependencies
([collection](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L5335-L5346)).
Original Android `textMentionName` carries recursive text and a 64-bit user ID
([carrier](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L717-L733));
the original layout attaches its user-mention span to the label
([renderer](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L2169-L2171)).
This establishes representation and rendering, not profile-opening behavior.

Current World snapshots expose the persona and bots in that persona's private conversations.
Rich content is stored and returned unchanged, and incremental message changes have no referenced
user dependency envelope. Supporting third-party identities therefore requires an explicit
admission/disclosure rule and projection boundary under [AGENTS.md](../../AGENTS.md).

## Recommended decisions

| Boundary | Proposed choice | Observable consequence |
| --- | --- | --- |
| Bot knowledge | A bot can mention itself or a synthetic user with an existing private conversation with that bot | Unknown IDs and users known only to another bot reject before publication. This is a documented synthetic access rule, not production Telegram entitlement. |
| Internal identity | Store recursive mention text plus `user_id`; resolve profile information from the owning World | Caller names/usernames/flags cannot spoof identity; current authoritative User data appears in Bot API output. No copied profile becomes a second authority. |
| Recipient disclosure | A visible message makes its referenced identity available to that recipient | Mentioning a third party intentionally discloses the same synthetic profile fields needed for public message interpretation. Other personas do not gain access. |
| Snapshot lifetime | Derive additional visible identities from currently visible stored messages | Removing the last reference removes the extra identity from subsequent snapshots. Previously informed clients may retain it; this is not a revocation guarantee. |
| Incremental dependencies | Supply authoritative referenced users in the same response as each batch of message changes, and apply them before decoding those changes | A newly mentioned user is available on first delivery, including after interruption or cold restart; no separate timing-dependent lookup is required. |
| Versioning | Introduce bridge snapshot/changes version 3 for the dependency envelope and ID-only mention shape | Existing version 1/2 reads remain unchanged when no visible mention requires the new contract; otherwise they fail explicitly before advancing a cursor or returning incomplete state. |
| Native identity fields | Reuse the bridge's explicitly supported synthetic User fields; do not automatically expose future Bot API-only fields | The native cache receives a defined representation, while the HTTP API independently projects its supported full User shape. |

Example: bot 4 already has private conversations with users 2 and 3. It sends user 2 the rich
label `Winner` mentioning user 3. The stored node is
`{"type":"text_mention","text":"Winner","user_id":3}`. The HTTP result uses
`{"type":"text_mention","text":"Winner","user":{"id":3,"is_bot":false,"first_name":"Mina"}}`
for the corresponding authoritative fixture user. Persona 2's version-3 snapshot contains user 3;
the incremental response carries user 3 as a dependency before applying that message. A separate
persona whose messages contain no such reference receives no new identity. Supplied forged names
do not affect any of these values.

Derive dependencies from the exact changes in a response, including older message versions being
replayed; derive snapshot dependencies from its current visible messages. Resolve each response
under one SQLite read snapshot. Message validation, identity access checks, no-op comparison and
publication remain atomic. A rejected send/edit or no-op cannot create visibility, allocate IDs,
or advance events. Current profiles have no mutation API; if one is added, define profile-update
delivery before claiming live cache freshness. ID-only historical content would project current
authoritative profile information at the HTTP boundary.

This recommendation avoids a separate permanent grant table. Durable grants would be appropriate
if later product behavior requires identities to remain discoverable after all references vanish,
but are unnecessary for this message-derived disclosure contract. Restricting mentions to the
current recipient and bot would avoid disclosure/version changes, but would leave third-party
mention scenarios unsupported. Making every World user globally visible would discard the
existing persona boundary and is not recommended.

## Acceptance before claiming support

Compare complete World/history/events and JSON/form Bot API send/edit/update results, normalized
no-op round trips using returned User objects, and exact native ID serialization. Exercise
recursive Persian/English labels, empty labels, duplicate and multiple references, self/recipient/
third-party mentions, forged profile fields, unknown or inaccessible users, malformed IDs and
independent Worlds. Rejection must preserve all state and subsequent identifiers.

Version-3 snapshot and incremental replay must agree on current messages and their identity
dependencies. Cover edit-add/edit-remove, an old change replayed after a later edit, truncated
change batches, already-known identities, bot/client restart and two recipients with different
references. Verify version 1/2 failures explicitly on visible unsupported content and unchanged
behavior in unrelated conversations. A native message must never be applied before its required
user dependency is available.

Use original `textMentionName` serialization and original bilingual rendering/live edit/cold
restart, retaining PNG/XML/report and account-free isolation evidence. No profile navigation,
automatic mention detection, real accounts, DC access or global directory is included. Media and
custom emoji remain required separate operational work.

After consultation, freeze the exact version-3 schemas and error rules before assigning separate
World/API and GPL adapter workers. The coordinator owns independent public/native acceptance,
version compatibility, source preservation, builds, merges and combined gates.
