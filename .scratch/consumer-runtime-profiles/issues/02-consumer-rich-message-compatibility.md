# Consumer rich-message compatibility

Type: implementation
Status: resolved
Work state: resolved
Blocked by: none

Accept the standard `disable_notification` parameter on `sendRichMessage`, matching Telegram's
rich-message method and requests emitted by common Bot API clients. Preserve URL and chosen-chat
inline-query button actions used by consumer catalogs. Preserve explicit rejection of unknown or
malformed input and verify both JSON and form HTTP requests through the public Bot API boundary.

## Comments

- 2026-09-13: Claimed after a contained external consumer reached GramLab and received
  `GRAMLAB_UNSUPPORTED: Bot API parameters` for its initial rich-message response.
- 2026-09-13: Added `disable_notification`, URL and chosen-chat button preservation, generated
  entity metadata, light/dark Android selection, client-exit diagnostics, and bounded automatic
  failure recordings. The rich-button native patch stages without fuzz and the rebuilt APK passes
  contained consumer scenarios in both themes. Focused Bot API, codec, runner, theme, and
  Android-host checks pass.
- 2026-09-13: Final generic main reconciliation passes all 1,608 non-Android tests at 88.96%
  coverage, full Ruff lint and format, source-package mypy, and configuration/link validation over
  295 Markdown files.

`0031-rich-auto-detection.patch` admits the approved scanner's five metadata-free canonical nodes
at the semantic adapter boundary and projects them into the pinned original `TL_iv.textMention`,
`textHashtag`, `textCashtag`, `textBotCommand` and `textBankCard` constructors. The serializer probe
round-trips those exact original types. It does not scan text on Android or change the renderer;
Python supplies the already canonical enriched tree. Host patch application and Android test
collection are worker gates; APK compilation and serialized native execution remain coordinator
acceptance.

`0032-atomic-media-groups.patch` negotiates bridge v6 and maps canonical positive signed-64-bit
album IDs to original `TL_message.grouped_id` with flag 17. It validates complete 2–10-member,
same-chat/same-kind contiguous topology in snapshots and creation changes, including response-wide
chat/message uniqueness and ordered contiguous grouped snapshot revisions. It admits the bounded
limit-plus-nine page expansion, classifies the exact split-cursor 409 for complete-snapshot recovery,
and applies each live group through one stock `TL_updates` envelope before advancing its cursor.
Version-6 response-local media/document/custom-emoji dependencies retain the established scope
checks, while complete snapshots retain their existing dependency superset. The patch changes only
adapter, transfer-route and serializer-observer seams; original message cells, grouped layout,
renderer resources and input handlers remain unchanged. The worker owns source staging and the
normal30 unsupported-v6 red; the coordinator owns the album-era APK build and green native codec.

`0033-rich-navigation-buttons.patch` extends the bridge-v6 rich-button codec with URL and
`switch_inline_query_chosen_chat` actions and preserves generated-entity metadata required by the
original constructors. URL and chosen-chat buttons remain original Telegram UI actions rather than
GramLab scenario input targets. The patch applies to the pinned source with zero fuzz or offsets;
the rebuilt APK SHA-256 is
`23d71d51e9db7e901d44df5381f1b2b8489fef844513f00403c7792c146059c0`. Focused native codec and
contained consumer light/dark rendering checks pass.
