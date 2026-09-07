# Local photos

The first photo profile accepts PNG and JPEG through `sendPhoto` and rich photo blocks, with
bot-scoped reuse/download and authenticated recipient delivery. The latest combined core gate
passes 510 tests at 81.98% coverage. The original Android codec passes four complete valid cases
and 24 rejection cases. Four controlled faults pass original failure/cleanup and explicit cold
restart recovery, with eight inspected captures and exact recovered JPEG bytes.

Normal23 passes original UI cancel/retry, shared-consumer loading and ordinary-edit global cleanup.
All nine captures are inspected. A canceled shared cell receives file-level completion without a
bitmap; ordinary replacement globally cancels the old shared transfer. A separate rich-photo
scenario keeps its leading photo unchanged while editing its second photo: the new JPEG binds
before the old shared PNG completes, and no old bitmap replaces the edited receiver. All 18 private
observer guards pass; four original captures and desktop/mobile reports are inspected. See
[ticket 49](../../.scratch/rich-messages/issues/49-media-native-interactions.md) and
[ticket 55](../../.scratch/rich-messages/issues/55-rich-photo-late-completion.md).

Fresh real-bot edit/restart acceptance also verifies exact phase-local native requests and bytes,
including original destination cleanup followed by JPEG reload. Four original captures and
reports are inspected. The separate unchanged-photo control also passes: the same original
image-directory bytes render after COLD restart with no new asset GET. Both captures and its
desktop/mobile report are inspected; see
[ticket 56](../../.scratch/rich-messages/issues/56-photo-lifecycle-cache-oracle.md). Preserve the
older failed JUnits and retained acceptance qualifications. Wider native regression, general
files/albums and custom emoji remain required; this is not complete media support. The
[shared contract](media-implementation-contract.md) defines the exact profile and bridge fields.

## Sending and reusing a photo

Send a multipart `sendPhoto` request to the run's local Bot API endpoint. Include the recipient's
Bot API `chat_id` and either a file part named `photo`, or a text field `photo=attach://image` with
a separate file part named `image`. Part names must be unique. Optional `caption`,
`caption_entities` and callback `reply_markup` use the existing message conventions; serialize
structured values as JSON in multipart text fields. Captions accept at most 1,024 code points.

The response has a `photo` array containing one full-size representation. Reuse its `file_id` in
another `sendPhoto` request from the same bot. `getFile` returns a stable relative `file_path`;
download it from the same local endpoint's `/file/bot<TOKEN>/<file_path>` route. The bot capability
and file ownership are checked again for downloads. Keep that capability-bearing URL out of logs.
Another bot cannot reuse this file ID; uploading the same bytes gives that bot its own identity.

## Rich photos

For multipart `sendRichMessage`, encode this object in the `rich_message` text field and attach
the PNG/JPEG as file part `image`:

```json
{
  "skip_entity_detection": true,
  "blocks": [
    {
      "type": "photo",
      "photo": {"type": "photo", "media": "attach://image"},
      "caption": {
        "text": ["Photo / ", {"type": "bold", "text": "تصویر"}],
        "credit": "Local fixture"
      }
    }
  ]
}
```

The rich caption has separate `text` and `credit` RichText members. Reuse a bot-owned file ID in
`media`, or replace the rich photo through `editMessageText` with `rich_message` and the new
attachment. Asset bytes are immutable: an edit changes the message reference and revision.
Old recipient grants remain valid for the World lifetime, including after reopening the World.

## Boundaries

GramLab detects format from bytes, fully decodes the image and stores the original validated
bytes. It does not reproduce Telegram server recompression or thumbnail generation. Invalid
images, unknown file identities and unsupported fields reject before publication. External media
URLs and host paths cannot supply image bytes. The [offline boundary](offline-safety.md) applies
to the bot, simulator and client throughout execution.

This batch does not add albums, general documents, animated media, custom emoji, photo spoilers,
thumbnails, HTML parse modes or ordinary `editMessageMedia`. These remain separate requirements.
Legacy bridge versions reject photo-bearing responses explicitly; the normal Android runner
selects version 3. Simulation captures include caption text but provide no image-rendering proof.
