# Custom emoji source contract

This note fixes the first custom-emoji boundary to the repository's pinned Telegram sources. It
describes source behavior, not production entitlement, and does not choose GramLab's storage or
delivery architecture.

## Bot API and TDLib shapes

At Bot API server commit `2efabc722e9493b9cac450233198d09e5cea0573`, an ordinary entity is:

```json
{"type":"custom_emoji","offset":0,"length":2,"custom_emoji_id":"5368324170671202286"}
```

The server accepts `custom_emoji_id` as a required decimal JSON string or number, parses it as a
64-bit integer, and serializes it as a decimal JSON string. The entity's covered text must be an
emoji. These are separate from the rich-text
object accepted by rich-text methods:

```json
{"type":"custom_emoji","custom_emoji_id":5368324170671202286,"alternative_text":"🙂"}
```

That example uses a JSON number; the same required-long decoder also accepts a decimal string.
The input requires `alternative_text`; output emits the ID as a string and includes the alternative
text. See the pinned server's
[entity encoder](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L622-L625),
[entity decoder](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L11914-L11916),
[rich-text decoder](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12214-L12217), and
[rich-text encoder](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L861-L865). The pinned TDLib schema supplies the
[covered-text and premium rule](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/generate/scheme/td_api.tl#L5778-L5779).

`getCustomEmojiStickers` accepts `custom_emoji_ids` as a JSON array whose elements must be decimal
JSON strings; the Bot API server converts them to TDLib integers. TDLib caps the list at 200 and
returns a `stickers` vector. Each returned custom-emoji Sticker joins the logical document ID
(`custom_emoji_id`) to its media `file`: the Bot API projection includes `file_id`,
`file_unique_id`, optional file size, width, height, format booleans, and optional thumbnail,
emoji, set name, and `needs_repainting`. `custom_emoji_id` is therefore not a file identity.
`file_id` is the reusable/download identity and `file_unique_id` is its stable comparison identity;
neither can replace the document ID used by a message entity. See the pinned
[request decoder](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L16687-L16714),
[Sticker projection](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L1057-L1112),
[file projection](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L17947-L17972), and
[TDLib method contract](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/generate/scheme/td_api.tl#L14750-L14751).
TDLib explicitly says results are in arbitrary order and include only found stickers. Duplicate-ID
behavior is not specified, so callers must correlate results by `custom_emoji_id` rather than
position.

## Android document and media boundary

The pinned Android client creates an animated-emoji span from an embedded `Document`, or from only
the entity's `document_id`. The latter resolves through memory, the `animated_emoji` SQLite table,
and finally `messages.getCustomEmojiDocuments`; a missing ID in a successful vector is requested
again. Offline fixtures therefore need a complete resolvable projection, not only an accepted text
entity. See [span construction](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MessageObject.java#L8006-L8036) and the
[document resolver](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/AnimatedEmojiDrawable.java#L193-L330).

The canonical Android `Document` carrier contains `id`, `access_hash`, `file_reference`, `date`,
`mime_type`, `size`, `dc_id`, optional `thumbs`/`video_thumbs`, and attributes. Its
`documentAttributeCustomEmoji` supplies `alt`, an `InputStickerSet`, and the `free` and
`text_color` flags. The renderer reads the document ID, MIME type, size, thumbnails and file
locations. These fields and valid file-location metadata form the minimum source-derived fixture
surface; fixed dummy values are acceptable only where the offline transport explicitly owns them.
See the pinned [Document definition](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L28383-L28577) and
[custom-emoji attribute](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L1925-L1947).

TDLib identifies the three sticker formats as WebP, TGS, and WebM. In Android, MIME
`application/x-tgsticker` loads the main document as Lottie and `video/webm` loads it as autoplay
video. The fallback static branch renders the closest document thumbnail, so a static synthetic
document must provide a usable WebP thumbnail and its bytes; a bare WebP main document is not
proven sufficient by this path. The established delivery seam is
`ImageLocation.getForDocument(...)` into `ImageReceiver.setImage(...)`, which reaches the normal
image/file loader. The special `absolutePath` constructor is video-oriented and does not prove a
general TGS/WebP contract. See the [TDLib format types](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/generate/scheme/td_api.tl#L403-L409) and Android's
[format and loader branches](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/AnimatedEmojiDrawable.java#L584-L684).
Locally authored assets may target those formats without importing Telegram assets. How GramLab
maps synthetic file locations to bytes, persists documents, and handles missing media remains an
architecture decision.

## Admission and presentation

The pinned TDLib contract says the covered text must be emoji and only premium users can use
premium custom emoji. Android's picker admits a candidate when the user is premium, the custom
emoji attribute is `free`, or the document belongs to the allowed default topic-icons set; its
emoji search also checks the attribute's `alt`. This is selection behavior. Span creation and
drawable initialization show no premium gate for an already received entity. Presentation is
instead conditional on resolving a document and usable asset. See Android's
[picker filtering](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/MediaDataController.java#L9131-L9268).

The pinned material does not prove the complete ordinary-chat server admission policy, bot
entitlement, custom-emoji sticker-set administration lifecycle, or behavior for every missing and
duplicate lookup ID. GramLab must therefore label synthetic acceptance as an offline policy rather
than real Telegram entitlement. Before implementation, the coordinator must decide:

- which synthetic IDs and sticker sets are admitted, including free/premium modeling;
- whether documents are embedded in updates, preseeded in Android storage, or resolved through an
  intercepted document request;
- how file locations map to locally authored bytes and how missing documents/assets terminate
  without the pinned client's repeated network fetch;
- which one static and one animated format constitute the first fixture matrix.

The existing GramLab entity validators support nine entity types and reject `custom_emoji`; no
document registry, `getCustomEmojiStickers` projection, or Android media delivery contract exists.
Implementation consequently spans validation, Bot API serialization, synthetic document lookup,
and media delivery. Adding the tenth entity type alone cannot meet the rendering milestone.
