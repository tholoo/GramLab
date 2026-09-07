# Local photos

The first photo profile accepts PNG and JPEG through `sendPhoto` and rich photo blocks.
Seventeen focused World, HTTP, bridge, contained real-bot and public capture checks pass.
All 471 non-Android tests pass at 81.71% coverage after restoring missing historical callback
journal events in migration fixtures. The original Android codec passes four complete valid cases
and 24 rejection cases. A contained real-bot photo/edit/restart scenario completes and its retained
observations pass corrected host assertions with original bytes unchanged. The original failed
JUnit is preserved; this is retained acceptance, not a relabeled green run. Original images and
reports have been inspected. Four controlled response faults (truncated, corrupt, redirected and
missing) also pass original Android failure/cleanup and explicit cold-restart recovery, with eight
inspected captures and exact recovered JPEG bytes. The first-photo cancellation fix passes retained native transfer/cache/binding assertions;
its loading capture needs a rerun after correcting capture order. Shared consumers, completion
after a live edit, wider native regressions and complete capture acceptance remain open; this is not complete media support. The [shared contract](media-implementation-contract.md) defines
the precise limits and bridge fields.

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
