# Rich photo source contract

Research checkpoint against Bot API server `2efabc722e9493b9cac450233198d09e5cea0573`,
TDLib `bc9c263e2bfee06aaab41e82db51a103376030bc`, and Android
`62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c`. This is source research only: no
server, bot, account, Android client or Telegram DC was used, and no native fidelity or
implementation support is claimed.

## Public request and response

The smallest documented request block for one original PNG is:

```json
{"type":"photo","photo":{"type":"photo","media":"attach://asset"}}
```

The multipart part named `asset` carries the PNG. The moving official
[InputRichBlockPhoto documentation](https://core.telegram.org/bots/api#inputrichblockphoto)
defines required `type: "photo"`, a required `photo` `InputMediaPhoto`, and an optional rich
block `caption`; it says the media object's ordinary caption is ignored. The moving
[InputMediaPhoto documentation](https://core.telegram.org/bots/api#inputmediaphoto) permits a
Bot API `file_id`, HTTP URL, or `attach://<name>` multipart reference. The general
[file rules](https://core.telegram.org/bots/api#sending-files) currently limit uploaded photos
to 10 MB and URL photos to 5 MB. A reused `file_id` retains every photo size, is bot-specific,
and may have multiple valid values for the same file. `file_unique_id` cannot download or resend
a file, as specified by [PhotoSize](https://core.telegram.org/bots/api#photosize). These pages
move independently of the immutable source pins.

The pinned server requires each block and its `photo` member to be an object and requires both
type strings to equal `photo`. Missing/empty `media` or an unresolved attachment yields
`media not found`. Its
[block parser](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12268-L12431)
passes no ordinary caption into the media parser, then separately parses the block caption. It
reads `has_spoiler` from the nested `photo` object and moves it to the result block, although the
current `InputRichBlockPhoto` table does not list that field. Width, height, thumbnail,
`show_caption_above_media`, `parse_mode`, `caption_entities`, and nested caption do not affect
this minimal projection. These are pinned source facts, not live-server evidence.

The pinned [file resolver](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L10758-L10802)
maps `attach://name` to the uploaded part; otherwise any nonempty string becomes an
`inputFileRemote`, including an HTTP URL or `file_id`. Local `file:/` paths work only in the
server's separate local mode. Remote-reference validity, MIME type, dimensions, ratio and bytes
are checked later, so the JSON parser alone does not establish acceptance. TDLib's pinned
[inputPhoto schema](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/generate/scheme/td_api.tl#L5830-L5837)
states at most 10 MB, width plus height at most 10,000, and aspect ratio at most 20. This server
path passes width and height as zero; the server may replace them.

The canonical response block is `{"type":"photo","photo":[PhotoSize,...]}` with optional
`caption` and truthy `has_spoiler`. Each `PhotoSize` has `file_id`, `file_unique_id`, width,
height, and optional nonzero `file_size`. The pinned
[photo serializer](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L2301-L2344)
omits TDLib sizes of type `i` and `t` and sizes with an empty remote identifier. The
[block serializer](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L4683-L4699)
omits the photo case when TDLib supplies no photo and emits caption/spoiler only when present/true.
Neither upload bytes nor an upload filename is therefore the returned public media identity.

## TDLib and Android projection

TDLib validates `inputPageBlockPhoto.photo` through ordinary photo message-content conversion,
then stores the resulting `Photo` beside the block
([conversion](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L5677-L5689),
[types](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/generate/scheme/td_api.tl#L6025-L6029)).
When producing protocol input, it consumes the next prepared media item, appends its `InputPhoto`,
and emits `pageBlockPhoto` with that ID. Without a reusable input photo, it substitutes a divider
([source](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/telegram/WebPageBlock.cpp#L3071-L3087)).

Pinned Android needs two matching pieces:

- `TL_iv.pageBlockPhoto` carries flags/spoiler, `photo_id`, caption and optional URL/webpage ID
  ([class](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L1217-L1251)).
- `TL_iv.RichMessage.photos` carries complete `TLRPC.Photo` objects
  ([class](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/tl/TL_iv.java#L195-L229)).

The IDs must match. `RichMessageLayout.getPhoto` searches that vector, and `RichPhotoBlock`
selects the closest full `PhotoSize`, optionally a stripped size, then calls original
`ImageReceiver` with `ImageLocation.getForPhoto`
([lookup](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L708-L713),
[block](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L7048-L7126)).
The `Photo` needs usable ID/DC/access-hash/file-reference metadata and an ordinary size with
positive dimensions/size and a usable location. Current `PhotoSize` deserialization synthesizes a
deprecated location from owning photo ID and size-type byte when the constructor lacks one
([source](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java#L43398-L43460)).
A direct in-memory projection must preserve that effective location; constructing `TL_photoSize`
alone does not run deserialization.

With no matching photo or selected full size, the block leaves the image empty. With no usable
location, `FileLoader.getAttachFileName` is empty and there is no download control
([naming](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/FileLoader.java#L1633-L1683)).
For a usable size, the client names the JPEG from location volume/local IDs, checks cache and
image directories, and decodes an existing file normally. If absent, `ImageLoader` delegates the
same `ImageLocation` to `FileLoader`; the original download/progress state remains visible and a
failed download returns to that state
([load branch](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/ImageLoader.java#L3229-L3275),
[state](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/messenger/RichMessageLayout.java#L6944-L7044)).

## Delivery inference and unresolved choices

The smallest faithful on-demand seam appears below `ImageReceiver`, at original `FileLoader`
requests for the projected `ImageLocation`. A GPL-side adapter could authenticate the active run,
obtain world-owned bytes, and complete the original cache operation under the path selected by
`FileLoader`, preserving original loading, decoding, caching, progress and retry behavior.
Pre-seeding proves decoding but not missing/on-demand behavior; an HTTP URL enters a separate Java
loader and widens offline-egress risk. This paragraph is design inference, not a chosen protocol.

GramLab currently has no multipart parser, media registration/store, public media identifiers,
photo-block validation, `Photo`/`PhotoSize` projection, authenticated byte endpoint, or GPL
file-loader completion seam. Its bridge rejects rich media and its request encoding excludes
multipart. User consultation is required for:

1. Asset identity/lifetime: allocated or content-derived identity; bot/world/run scope; persistence
   across edits, restart, reset and reports; `file_id` versus stable non-downloadable
   `file_unique_id`.
2. Registration shape: multipart `attach://`, a narrower local API, or both; errors for duplicate
   names, missing parts, invalid PNG, dimensions/ratio/size, wrong type and stale IDs.
3. Authenticated delivery: endpoint/process boundary, run capability, allowed asset/range, path
   defenses, and rejection before any native/DC/HTTP fallback.
4. Cache/loading semantics: materialization timing, interrupted/partial loads, cache ownership and
   cleanup, edit retention, missing-byte retry/failure presentation and deterministic progress.
5. First scope: one static PNG without caption/spoiler, or caption, spoiler, reusable IDs, multiple
   sizes, edits and cold restart in the first accepted profile.

No fixture filename is a proposed public media ID. After approval, work can split into core
validation/storage, GPL projection/delivery and real-bot native acceptance. That split is planning
guidance, not an interface decision.

## Caption normalization clarification

The pinned server's `get_page_block_caption` (`Client.cpp` 12057–12069) reads a
RichBlockCaption object with optional `text` and `credit` RichText members; a nested `blocks`
message is not that shape. `JsonRichBlockCaption` (980–990) always emits text and emits credit
when present. TDLib's `WebPageBlockCaption::get_page_block_caption_object`
(`WebPageBlock.cpp` 853–859) omits the entire caption when both members are empty plain text;
otherwise it emits text and omits empty plain credit. `RichText::empty` (415–417) means empty
plain text specifically, not an empty nested wrapper. These observations use the same recorded
immutable source pins; they do not expand the admitted RichText types or prove native rendering.
