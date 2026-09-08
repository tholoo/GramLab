# Edit standalone ordinary photos and documents through the real Bot API

Type: task
Status: ready-for-agent
Work state: open
Blocked by: none for World/HTTP implementation; native acceptance remains coordinator-owned

Implement the next required media-edit slice within the approved media architecture and the
[document contract](../../../docs/development/documents-implementation-contract.md). The full
operational milestone still requires albums, default classification and original native acceptance.
This task covers both caption-only edits and replacement of standalone ordinary photo/document
messages; it is not full editMessageMedia compatibility or operational completion.

## Ownership

Own this ticket, the necessary edit seams in `src/gramlab/world.py` and `src/gramlab/bot_api.py`,
new `tests/test_media_edits_world.py` and `tests/test_media_edits_http.py` only. Read existing tests
and reuse real collaborators, but request ownership before changing an existing test or another
production module. Coordinator owns shared docs/contracts, native patches, CI, runner, lockfiles,
merges and combined/native gates. Use a separate task branch/worktree and checkout-local environment.

## Pinned source basis and limits

Bot API server revision `2efabc722e9493b9cac450233198d09e5cea0573` parses
[media edits](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L14762-L14810),
[caption edits](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L14812-L14861),
[InputMedia](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L12793-L12878)
and returns a complete reloaded
[edited Message](https://github.com/tdlib/telegram-bot-api/blob/2efabc722e9493b9cac450233198d09e5cea0573/telegram-bot-api/Client.cpp#L6999-L7024).
Verify those pinned definitions before implementation. TDLib revision
`bc9c263e2bfee06aaab41e82db51a103376030bc` describes the
[edit operations and album restrictions](https://github.com/tdlib/td/blob/bc9c263e2bfee06aaab41e82db51a103376030bc/td/generate/scheme/td_api.tl#L12324-L12338).
These are source contracts, not live server evidence. Keep source adaptation out of the MIT core;
write independent behavior and use reviewed existing metadata/resolver helpers.

A missing caption parses as empty; missing markup becomes absent markup. Both operations replace
those fields rather than preserving omitted old fields. Caption-only edits preserve the media.
Standalone photo/document replacements may cross those two kinds. Preserve creation identity/date,
set edit_date from the existing World clock, and emit one existing message.edited revision/change.
No new message/update ID is allocated. Exact remote no-op/error wording and server time windows
are not established here; retain the existing deterministic local MESSAGE_NOT_MODIFIED profile.

## Frozen World interface

Add `World.edit_caption(*, chat_id, message_id, bot_id, caption=None, caption_entities=None,
reply_markup=None)` and `World.edit_media(*, chat_id, message_id, bot_id, media, uploads=None,
caption=None, caption_entities=None, reply_markup=None)`.

`media` has exactly `type` (`photo` or `document`) and `media` (one attach://NAME or same-bot typed
file ID). Photo upload values are exact bytes; document upload values are DocumentUpload. A single
uploads mapping may be typed as bytes | DocumentUpload, but only the selected kind and attachment
are admitted. Use the existing resolvers and independently typed identities; no content sniffing
or conversion of one kind's reusable file ID into the other. World calls explicitly select a kind;
the HTTP detection flag remains HTTP admission policy.

Require a standalone ordinary photo/document message in the sending bot's private chat. Reject
ordinary text, rich content and grouped messages explicitly in this slice; extending their edit
forms remains separate work. Omitted/empty captions remove caption/entities; omitted markup removes
the keyboard. Reuse current caption length/entity/custom-emoji and inline-keyboard admission.
Do not silently widen ordinary caption mention support or add new formatting/detection rules.

Resolve uploads, validate full input, check ownership/equality, retain/add grants and publish the
message/revision in one caller-owned writer transaction. A no-op or any failure must roll back
new bytes, file identities, grants and allocation as well as message/event state. Preserve old
photo/document/custom-emoji grants and immutable historical dependencies after replacement.
Schema9 and the existing edit_date/revision machinery already provide the necessary storage seam;
report any contrary evidence before changing persistence or bridge versions.

## HTTP interface

Expose editMessageCaption and editMessageMedia with chat_id/message_id and optional reply_markup.
For editMessageCaption admit caption/caption_entities and false or omitted show_caption_above_media.
For editMessageMedia require InputMediaPhoto or InputMediaDocument, with nested media, optional
caption/caption_entities and applicable document disable_content_type_detection. New document
uploads require explicit true under the existing forced-file profile; typed reuse retains its kind.
Allow direct named multipart attachments through attach:// and JSON/form/query equivalents where
already supported. Return the complete edited Bot API Message, including edit_date and exact media.

Reject parse modes, inline/business edits, thumbnails, URLs/host paths, unsupported flags/options,
true show-caption-above, spoilers and extra/unused/duplicate/missing attachments explicitly.
Keep those unsupported surfaces in the full inventory. Preserve existing sendPhoto/sendDocument
limits. editMessageMedia may need the existing document-sized multipart envelope because nested
kind is not known before parsing; preserve per-kind photo/document byte admission and all text,
header and part-count bounds. Caption-only edits never admit uploads. Do not widen other routes.

## Acceptance and handoff

Follow TESTING.md: retain an actual World/HTTP unsupported-operation red before production changes.
Use independently specified complete responses/messages/events/revisions/dependencies. Cover
photo→photo, document→document, photo↔document, same-bot reuse/new uploads, caption-only media
preservation, caption/entity/keyboard replacement/removal, custom-emoji admission/retained grants,
old callback/history dependencies, exact getFile/download bytes and reopen. Invalid ownership,
cross-kind/cross-bot IDs, malformed caption/keyboard/attachments, unsupported forms and complete
no-ops must preserve the complete logical database. Include late-publication rollback and retry;
reuse authentic existing World/HTTP fixtures without substituting the SQLite/HTTP boundaries.

Run focused new World/HTTP checks plus affected existing photo/document/edit/callback/migration
checks with fatal ResourceWarning in the outer offline namespace. Run scoped strict mypy and Ruff.
Keep 50MB boundary fixtures sequential and clean temporary databases after preserving evidence.
No full gate, Android build/guest, dependency change, upstream export or external runtime traffic.
Freeze a clean exact branch tip and report source references, red/green results, terminal processes,
shared-doc impacts and remaining native/album/classification requirements. Coordinator reviews,
merges and runs combined verification; worker-only checks do not close this ticket.
