# Proposed atomic photo and document albums

Status: proposed architecture and fidelity contract; unapproved and not implemented.

This proposal turns the [album source findings](albums-references.md) into a bounded first
implementation. Source-backed rules are separated from local choices about identity, aggregate
memory, rollback and client pagination. Those choices require user approval before schema or bridge
work starts.

## Source-backed surface

The first operational profile would expose Bot API `sendMediaGroup` with an ordered JSON array of
2–10 members. It admits only the two media families GramLab already implements:

- all-photo groups; or
- all-document groups.

Every member has its own caption and caption entities. The method has no reply markup. Mixed
photo/document groups and all unsupported InputMedia types reject. New document uploads in an album
always use forced ordinary-file behavior, even if the member supplies false or omits
`disable_content_type_detection`. A successful response is an ordered array of Messages sharing a
`media_group_id`.

The proposed first-profile request admits only top-level `chat_id` and `media`. The `media` value is
an array in JSON and a JSON-encoded string in form or multipart requests. An exact photo member has
`type`, `media`, and optional `caption`, `caption_entities`, or
`show_caption_above_media`; a document member additionally admits optional
`disable_content_type_detection`. Omitted or false `show_caption_above_media` is accepted and true
rejects. `parse_mode`, spoiler, thumbnail and every other item or top-level field reject. Captions
use the existing 0–1,024-code-point and explicit-entity/custom-emoji-grant contract. A supplied
document detection flag is type-checked but ignored after validation because album documents are
always forced ordinary files.

Original Android must receive the group through its existing `TL_message.grouped_id` flag and stock
grouping paths. Repeating standalone sends is not an album and is not an acceptable implementation.

## Proposed local contract

### Admission, bounds and publication

Each item keeps its existing typed rules: decoded PNG/JPEG photos are at most 10,000,000 bytes and
ordinary documents are nonempty and at most 50,000,000 bytes. The proposed album aggregate is
`sum(file_size(member) for every ordered member) <= 100_000_000`, including every occurrence of a
duplicate upload reference or reused `file_id`. The same `attach://NAME` may be used by multiple
same-kind members; each distinct upload part must be referenced at least once, and missing or unused
parts reject. Separately, the sum of distinct uploaded part payloads is at most 100,000,000 bytes,
`Content-Length` is at most 100,200,000 bytes, and the existing 64-part and 65,536 text-byte parser
bounds remain. These exact decimal bounds are local safety choices, not Telegram limits.

One deep interface,
`World.send_media_group(chat_id, sender_id, media: list[dict[str, Any]], uploads: Mapping[str, bytes | DocumentUpload] | None) -> list[Message]`,
would resolve and validate every item and attachment, then publish the complete group in one
`BEGIN IMMEDIATE` transaction. Pure byte decoding may happen before the lock, but all database-backed
reuse resolution, group/message allocation, inserts and grants occur within it. A private batch
publisher constructs each final canonical message before inserting its message, event and revision;
it must not call `send_photo` or `send_document` repeatedly or insert incomplete placeholder events.

The transaction allocates contiguous chat message IDs. Messages, group ordinals,
`message.created` events, revisions/client positions and the returned Bot API array follow input
order. Typed identities and recipient grants commit atomically while retaining their existing
deduplication and lifetime behavior. Any early or injected late failure rolls back every logical row
and allocation; retrying the same request after a failed transaction receives the same next IDs.

The group uses a World-wide positive signed-64-bit value in `1..2^63-1`, allocated by a transactional
counter and projected publicly as a canonical decimal string. Every World message and public Bot API
Message copies the same value. It remains stable across history, changes, edits and reopen.
World-wide scope, monotonic allocation and rollback-safe reuse are GramLab policy; the reviewed
sources do not establish Telegram's server allocation.

Schema 10 freezes that identity with these logical tables and equivalent SQLite constraints:

- `media_group_counter(singleton PRIMARY KEY CHECK singleton=1, last_id CHECK 0..2^63-1)`, seeded
  with zero;
- `media_groups(id PRIMARY KEY CHECK 1..2^63-1, chat_id REFERENCES chats, kind CHECK
  photo/document, member_count CHECK 2..10, UNIQUE(id, chat_id))`; and
- `media_group_members(group_id, ordinal CHECK 0..9, chat_id, message_id,
  PRIMARY KEY(group_id, ordinal), UNIQUE(chat_id, message_id), FOREIGN KEY(group_id, chat_id)
  REFERENCES media_groups(id, chat_id), FOREIGN KEY(chat_id, message_id) REFERENCES
  messages(chat_id, id))`.

Allocation increments `last_id` inside the publication transaction and rejects cleanly when it is
already `2^63-1`. Fresh creation and the populated 9→10 migration create the same schema; migration
leaves group tables empty, preserves every existing row byte-for-byte, passes foreign-key checks and
writes the version last under concurrent openers.

### Versioned complete-group delivery

Bridge v5 remains byte-for-byte strict. A new v6 keeps v5's topology and adds an optional canonical
`media_group_id` to grouped messages across snapshot, changes, messages, GET/POST callbacks, assets,
documents and custom-emoji-document routes. Older bridge versions reject grouped snapshot, change
or callback content before moving a cursor or accepting an action; unrelated legacy content remains
unchanged.

Snapshots contain every member of every visible group. For v6 changes, `after` is invalid only when
it lies strictly between the first and last creation positions of a group; standalone positions,
group-final positions and isolated edit positions are valid boundaries. An invalid cursor returns
HTTP 409 with schema 6 and error code `resnapshot_required`, message
`Client cursor splits a media group`, without mutation. The Android adapter responds by fetching and
reconciling a complete v6 snapshot, setting its cursor to that snapshot's position, then resuming
changes instead of retrying the bad cursor.

A changes page first selects the next `limit` rows. If its trailing row is within a grouped
`message.created` run, it appends the rest of that creation run. Thus it returns from one through
`limit + 9` rows, at most 1,009 when `limit=1,000`, and its cursor is the final returned position.
Grouped edit rows do not trigger expansion. Changes, difference and callback dependencies are exact
for every member in the expanded response. Snapshots retain the existing superset of all persona
grants, including historical media no longer referenced by current messages.

The Android adapter validates positive canonical IDs, one contiguous occurrence of each group ID per
response/chat, and complete 2–10-member same-chat/same-kind creation runs with contiguous message IDs
and client positions. Every member is bot-sent typed media; duplicate message IDs, nonmedia members,
standalone interleaving, reordered members and disjoint reuse of a group ID reject. Snapshot order
is validated against persisted membership; a grouped `message.created` changes run must be complete.
If grouped edits are approved, one `message.edited` row instead validates against already-known
immutable membership and is not mistaken for a partial creation run.

The adapter maps the ID to `TL_message.grouped_id`, sets flag 17 and applies one live creation group
in one stock `TL_updates` envelope. It advances its event cursor once, from the pre-group position to
the group-final position, only after the whole batch succeeds. Difference and cold-snapshot paths
preserve the same topology. Adding the field without group-aware paging, recovery and one-batch
native application is insufficient.

### Grouped edits

The recommended first slice keeps grouped `editMessageCaption` and `editMessageMedia` explicitly
unsupported. Send-time captions and true original layouts are still covered, while the album
storage and delivery invariant stays small enough to verify.

An optional wider slice would admit caption edits and same-kind member media edits only, preserving
group ID, ordinal and membership. It would never regroup, reorder, add or remove members, and would
reject cross-kind changes. That option requires lineage-aware bridge validation because a legitimate
edit change can contain one grouped member rather than a complete creation run.

## Choices requiring approval

1. Use the exact first-profile fields and repeated-attachment behavior above, the 100,000,000
   logical-byte aggregate counted per member, and the separate physical multipart bounds.
2. Use schema 10's rollback-safe, World-wide, monotonic positive signed-64-bit group-ID namespace
   and membership tables.
3. Add bridge v6 with complete-group page expansion of at most nine rows, inside-group cursor
   rejection and one-batch native application.
4. Keep grouped edits unsupported in the first album slice, or widen the slice to caption and
   same-kind media edits that preserve membership.

## Implementation and acceptance boundary

The core needs schema migration/reopen tests, a single atomic World publisher, strict JSON/form/
multipart Bot API parsing, ordered projection and group-aware bridge tests. Failures must cover
0/1/11 members, mixed kinds, bad or foreign IDs, cross-kind reuse, repeated/missing/unused
attachments, invalid fields/captions, every per-item/logical/physical aggregate boundary, late
publication faults and deterministic retry. Complete logical database state must match before and
after every rejected operation. Expanded v6 pages must carry exact sorted asset, document,
custom-emoji and user dependencies for all appended members while nongrouped v5 remains exact.

The GPL adapter must be a new reviewed patch over the original renderer, not a recreated album UI.
Native acceptance must show an initial two-photo collage with one first-member caption and a live
two-document group with distinct ordered filenames/captions. Arbitrary per-item photo captions are
proved semantically at World/Bot API rather than inferred from collage presentation. Deliberately
truncate the second document member's first transfer after its sibling succeeds: the complete
two-member group remains, the original radial retry succeeds, successful-request counts are one and
two respectively, final/presentation/cache bytes are exact, no partial file remains, and cold restart
issues zero new GETs.

Evidence combines decoded grouped IDs/flag17, one live `TL_updates` application and one cursor
transition with screenshot/XML geometry and document-row order. Any added group observer is opt-in
GPL adapter instrumentation and does not alter layout decisions. The public runner deterministically
uses one contained bot: it sends the initial photo group, the scenario captures it and sends a native
composer trigger, the same bot receives that trigger and sends the live document group, and the
scenario captures it. Compare complete Bot API responses, World history/events, v6 changes and both
original captures; the focused native gate, not repeated public captures, owns cold-restart proof.

After host fixtures and static checks settle, normal30 supplies the expected bridge-v6 rejection and
the coordinator builds and records one normal31 APK. Exactly three serial Android runs use it without
rebuild: focused album acceptance, public v6 runner acceptance, and one final current-APK Android
regression after its case inventory proves no skips. Retire each AVD and hash-verified duplicate APK
copy promptly, retaining one immutable normal31 APK and the required results, logs, screenshots and
reports.
