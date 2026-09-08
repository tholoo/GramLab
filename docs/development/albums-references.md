# Album source findings

This is source evidence for the required album work, not a frozen implementation contract or
completed compatibility. It extends the approved [media direction](../adr/0005-local-media-and-client-interaction-boundaries.md).

## Pinned Bot API and TDLib behavior

Bot API revision `2efabc722e9493b9cac450233198d09e5cea0573` parses each member's caption/entities
through InputMedia, invokes album-aware parsing for the media array, and sends one TDLib album
request. The route supplies no reply markup. Album document input forces ordinary-file detection
disabled even when the caller omits the flag or supplies false; standalone sendDocument does not
apply that override. See [InputMedia](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12794-L12864),
[array parsing](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12997-L13010),
[album dispatch](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L14505-L14564)
and [standalone documents](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L14057-L14070).

TDLib revision `bc9c263e2bfee06aaab41e82db51a103376030bc` specifies 2–10 members and supports
photo/video/audio/document content. Documents and audio require same-kind albums. Thus photo-only
and document-only albums are valid; mixing photos and documents is invalid. Captions belong to
individual members, with a shared caption-above setting. See [sendMessageAlbum](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/generate/scheme/td_api.tl#L12202-L12209).
These sources do not establish remote group-ID allocation or server failure atomicity.

## Original Android grouping

At Android revision `62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`, the original Message wire object
carries grouped_id under flag 17. MessageObject owns group layout and document/caption handling;
ChatActivity collects members during history and live delivery. Reuse these original paths;
sending unrelated standalone rows does not establish album rendering.
See [wire field](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L58336-L58337),
[group layout](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessageObject.java#L1251-L1389),
[history](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java#L21158-L21214)
and [live grouping](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java#L25764-L25788).

## Identity correction and implementation seams

An initial web raw response exposed a different 18,706-line Client.cpp despite a pinned-looking
URL. Its earlier line citations are discarded. The retained source matching the established
[media-edit references](../../.scratch/rich-messages/issues/106-standalone-media-edits.md) has 20,036
lines and SHA-256 `2fe7fa08933da86ee841195813c219dd0d4144f3f281bd29b4275ec7780dc0a8`.
The retained TDLib schema has 16,313 lines and SHA-256
`98b21543066e0124623b7d36f6496ef38cf86e9f9825aedcdd8e2527633fee4c`.
Revision binding uses the prior exact-ref acquisition; the files contain no embedded revision.
Android references were regenerated from pristine Git objects, not the patched build tree.

Current World photo/document resolvers and caller-owned writer transactions can support one atomic
local album publication. Calling standalone public send methods repeatedly would expose partial
success. Before assigning implementation, specify persistent group identity, complete message/event
publication, aggregate upload bounds, and versioned complete-group client delivery across pagination,
edits and restart. These are unresolved implementation seams, not evidence of Telegram's server
internals. Keep full album acceptance in the operational milestone.
