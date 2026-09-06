# Rich messages through the shared world and original Android renderer

Status: incremental implementation within the approved full feature inventory.

The next vertical slice carries structured rich messages through real Bot API HTTP requests,
SQLite world persistence, client snapshots/events/recovery, and the original Android rich layout.
Follow Bot API 10.3 and the pinned Android source; this is not a formatted-text substitute.

## Shared contract for parallel work

- The independent world message gains `rich_message`, shaped like the official output RichMessage:
  `blocks` and optional `is_rtl`. Existing identifiers, dates and journal/cursor contracts remain.
- For existing internal consumers, a rich-only world message may retain `text: ""`; this is not a
  flattened rendering fallback. The Bot API response omits ordinary `text`/`entities` for rich-only
  messages and returns `rich_message`. No Android-derived types enter the Python core.
- Implement `sendRichMessage` with block input and `editMessageText` with `rich_message` at the
  existing authenticated HTTP boundary. Unsupported methods/parameters/content fail before mutation.
- The initial shared block set is paragraph, heading, pre, footer, divider, blockquote,
  expandable_blockquote, pullquote, table and details. RichText strings, arrays and formatting
  wrappers support nested text. Core and adapter workers must exchange the exact supported wrapper
  and optional-field set before committing; source contradictions go to the coordinator.
- HTML/Markdown parsing, automatic entity detection, media, buttons, links, lists, custom emoji and
  streamed drafts remain in the full inventory. Do not silently accept those inputs without their
  semantics. Establish and report the precise boundary, including skip_entity_detection behavior.
- The Android adapter reads `message.rich_message` and constructs the pinned native RichMessage
  objects. Preserve original renderer code. Same structured content must survive snapshot, edit
  events and restart; ordinary messages keep their current behavior.

Core and adapter workers own separate files. The coordinator integrates them, supplies the real
bot/native scenario, reviews visual evidence and updates shared compatibility/handoff records.
