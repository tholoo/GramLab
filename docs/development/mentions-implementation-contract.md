# Explicit rich-mention implementation contract

This freezes implementation details of the already approved
[mention proposal](rich-mention-proposal.md) and [ADR 0005](../adr/0005-local-media-and-client-interaction-boundaries.md).
It does not claim runtime support. Use the existing media-enabled bridge version 3; no new route,
World schema migration, persistent identity grant or global directory is introduced.

## Input, persistence and output

Bot API input is exactly the outer node `{type: "text_mention", text: RichText, user: User}`.
The `user` object must contain an integer `id` from 1 through 2^63−1; booleans, floats, missing,
zero, negative or larger IDs reject. Other supplied User fields are accepted under existing
JSON duplicate-member/depth/node/string/size budgets and discarded. They cannot spoof identity.
A returned full User can be fed back into send/edit. Outer unknown fields still reject.

Canonical stored/client content is exactly `{type: "text_mention", text: RichText, user_id: ID}`.
The label recursively follows existing RichText validation and cleaning, including empty labels
and nested wrappers. Only the World admission resolver decides whether a validated ID is known:
a bot may mention itself or an existing user with a private conversation with that bot.
Unknown or inaccessible IDs reject atomically before allocating IDs or publishing anything.
Validation, admission, canonical no-op comparison and publication share the write transaction.

HTTP output replaces canonical `user_id` with the complete authoritative User from the owning
World, and recursively projects `text`. All message surfaces, including sends, edits, history and
updates, must use the same projection. Public Python World content remains ID-only; the HTTP API
is the User projection boundary. No profile mutation API is added.

## Identity envelopes and compatibility

The native User schema remains required `id`, `is_bot`, `first_name`, optional `username` and
`language_code`, with existing exact type/field validation. Each v3 response has a sorted,
deduplicated `users` list, resolved in the same SQLite read snapshot as its message data:

- Snapshot: existing persona/conversation-bot identities plus references in current visible messages.
- Changes: existing persona/conversation-bot identities plus references in precisely the selected
  change bodies, including historical bodies replayed after a later edit removes a mention.
- Callback response: existing persona/conversation-bot identities plus references in that
  callback's frozen message version.

Removing the last mention removes the extra identity from subsequent snapshots; previously
informed native clients may retain it. This is message-derived disclosure, not revocation.
Different recipients derive different envelopes. Existing media assets, revisions and replay
semantics remain unchanged.

Versions 1/2 reject any response whose selected/current message content contains a mention with
`GRAMLAB_UNSUPPORTED: rich mentions require client bridge v3`, using the existing unsupported
error mapping. Rejection occurs before callback publication/cursor advancement or partial output.
Conversations and selected change batches without mentions preserve existing behavior, including
existing photo rejection rules. A no-op edit using a returned full User remains MESSAGE_NOT_MODIFIED.

The GPL adapter validates and installs dependencies before decoding/applying any dependent
snapshot, change or callback message. It admits newly disclosed IDs, rejects duplicate dependency
IDs, rejects conflicting supported fields for an already known ID (profiles currently cannot
mutate), and rejects a mention without its known identity dependency. Map canonical content into
original `TL_iv.textMentionName` with its original recursive text and 64-bit ID. Preserve exact
serialization and existing strict link/media validation. No navigation, mention tap, automatic
entity detection or synthetic renderer is added.

## Parallel ownership and acceptance

The coordinator owns this contract, shared docs, merge order and combined verification. A core
worker owns admission, canonical/public projection and dependency derivation with new focused
World/HTTP/bridge tests. A separate GPL worker can use the frozen neutral schema. An independent
real-bot/native acceptance worker consumes these contracts; workers do not derive expected values
from the production serializer being tested.

Acceptance is the full matrix in the approved proposal: self/recipient/third-party identities,
forged claims, invalid/inaccessible IDs, output-to-input and atomic no-op behavior, recursive
Persian/English labels, duplicate references and budgets, edit add/remove, old/truncated replay,
callback identity dependencies, persistence, two recipients/Worlds and explicit legacy rejection.
Original native ID serialization and rendering/live edit/cold restart remain required before
claiming support. Core checks alone do not prove original mention rendering.
