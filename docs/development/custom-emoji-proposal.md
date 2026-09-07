# Proposed custom-emoji fixture catalog and original delivery

Approval covers the recommended decisions below. References to future consultation describe the
original proposal stage; do not request this approval again. Further consequential changes outside
these decisions still require consultation. Mini Apps remain deferred, and runtime Internet/DC
access and artifact publication remain excluded.

Status: approved by the user on 2026-09-07; implementation and acceptance remain incomplete.

Support registered local custom emoji in outgoing rich messages and button labels, ordinary
message entities, and incoming user updates. Resolve their documents and bytes through the
original Android loaders. The first required visual matrix includes static WebP and transparent
VP9 WebM, with usable thumbnails; TGS remains additional coverage and cannot substitute for WebM.
The [source contract](custom-emoji-references.md) establishes the distinct entity, document and
file identities and the original static/animated loader branches.

## Recommended choices

Use a trusted scenario operation to register original media in a persisted, World-wide fixture
catalog. This is explicitly synthetic setup, not an invented Bot API sticker-administration
method or proof of Telegram entitlement. Registration accepts a caller-selected positive signed
64-bit logical ID, or allocates one when omitted. Selected IDs support applications whose content
already contains configured IDs. An ID is namespaced by its World and never authorizes file reads.

Bind each registration atomically to an idempotency key and canonical request content. Repeating
the same request returns the same descriptor; conflicting key/body or ID/body bindings reject
without creating assets or advancing identifiers. Catalog entries and media are immutable for the
World lifetime. Numerically equal logical IDs in different Worlds may refer to unrelated original
fixtures; isolation comes from the owning World and authenticated operations, not global numbers.

| Boundary | Proposed behavior |
| --- | --- |
| Neutral catalog | Persist logical ID, catalog fallback, format, dimensions, repainting/free presentation metadata and immutable main/thumbnail asset references. Keep original Android Document/cache fields in the GPL projection. |
| Synthetic admission | Any bot or persona may reference an existing ID in its own World catalog. Unknown IDs reject before message publication. This models fixture availability, not production ownership or premium entitlement. |
| Message fallback | Preserve supplied rich `alternative_text` after normal cleaning; preserve the covered ordinary message text and UTF-16 entity range. Catalog fallback supplies Sticker/document metadata and does not rewrite message text or impose equality. |
| Bot lookup | Standard `getCustomEmojiStickers` projects registered entries and issues that caller's bot-scoped file identities. A second bot can look up the same catalog entry but cannot reuse the first bot's `file_id`. |
| Bot download | Reuse approved standard `getFile` and authenticated local file delivery for that bot's returned identities. Logical emoji ID and `file_unique_id` are not download capabilities. |
| Persona access | Publication grants the recipient access to referenced document metadata and main/thumbnail bytes atomically. Another persona cannot discover or fetch a document merely by guessing its logical ID. |
| Native resolution | Keep message entities ID-based and intercept original custom-emoji document requests. Supply canonical Documents only for authorized local entries, then let original memory/SQLite caches and image/file loaders operate. |
| Media lifetime | Reuse the proposed photo publication grants and immutable bytes; retain old grants after edits until World reset/deletion, including in-flight and restart recovery. |

The public lookup API caps requests at 200 decimal-string IDs and returns only found entries,
in arbitrary order; unknown IDs are omitted there. Whole-batch failure below applies only to
native document requests, not to this public Bot API method.
Freeze duplicate handling as an explicitly documented local policy before implementation; callers
must correlate results by logical ID. Do not copy a consumer-side limit into the API contract.
Sticker-set creation, transfer and premium entitlement need their own contracts; observing their
administrative prerequisites does not justify imposing owner-bot restrictions on message use.

## Shared media dependency and failure behavior

This proposal depends on the [pending photo architecture](rich-photo-proposal.md): World-owned
immutable bytes, bot file identities, authenticated persona delivery and the GPL FileLoader seam.
It must not establish a duplicate emoji-specific transport while that decision is pending.
Extend the shared neutral asset descriptor for document and thumbnail references, and coordinate
the bridge version with [mention dependencies](rich-mention-proposal.md) before parallel work.
Older clients must reject unsupported content explicitly rather than silently omit emoji.

Start original visual acceptance from an empty dedicated document/file cache. A valid ID should
trigger the original document request, return its complete neutral-to-native projection, and load
the main/thumbnail bytes through authenticated local delivery. Encoding/decoding fixtures is
preparation evidence only; it does not establish original animation or loading behavior.

The pinned Android resolver retries missing IDs after a partial successful Vector. Its non-Vector
branch does not perform that recursive request
([resolver](https://github.com/DrKLO/Telegram/blob/62b56a07ca7e30e39f7fd00a6728d6bbd716ca1c/TMessagesProj/src/main/java/org/telegram/ui/Components/AnimatedEmojiDrawable.java#L306-L330)).
Propose a whole-batch error for unknown or unauthorized native IDs, with no external fallback.
Authenticate the persona and validate/authorize the complete bounded batch before serializing
any document. Unknown and ungranted IDs must have the same bounded error shape, with no partial
metadata or per-ID existence detail; no timing-equivalence claim follows from that rule.
That branch alone does not prove visible failure, released callbacks or later recovery. Inspect
and test those effects before freezing the complete error contract. Missing/interrupted bytes
must follow the shared length/digest validation and atomic cache completion rules.

Bind each dedicated Android guest and its document/file caches to one World lifetime. Recreate
that state before using another World with potentially equal chosen IDs; persona authorization
alone cannot prevent an original cache from displaying stale bytes. Synthetic file locations
must identify immutable catalog content within that World. Reusing guests across Worlds would
need a separately verified cache invalidation/namespace contract.

## Acceptance and parallel work

Use original public fixtures to cover chosen and allocated IDs, registration retries/conflicts,
two bots resolving one catalog entry with distinct file identities, differing message/catalog
fallbacks, ordinary and recursive rich content, rich button labels, incoming UTF-16 entities,
send/edit/no-op, lookup/download, persistence and restart. Compare complete HTTP/update/World/
history/event/snapshot results and unchanged state after rejection. Unknown IDs, malformed
entities/assets, foreign bot file IDs and ungranted personas must fail at their public boundaries.

On Android, prove empty-cache lookup and delivery, static transparency, actual changing WebM
frames with transparent regions, live edits, cache reuse and cold restart. Retain original visual
evidence under an explicit capture policy; a still frame cannot prove animation. Exercise missing
documents, mixed authorized/unauthorized lookup batches, interrupted bytes, stale completion
after edit and reset/deletion. Verify independent external/DC/DNS denial and World/persona cache
separation. Simulation must match semantic state without claiming decoding, caching or rendering.

Original fixture work is independent and assigned in
[ticket 35](../../.scratch/rich-messages/issues/35-original-custom-emoji-fixtures.md). After
consultation, freeze catalog/file/document/error schemas together. Then assign separate core/API,
GPL document/loader and independent scenario tasks; the coordinator owns integration, builds,
guests and combined acceptance. Table/helper names and fixture artwork are routine choices.
The consequential decisions for review are the World-wide synthetic catalog/admission policy,
recipient document/media disclosure and the shared authenticated media architecture. None of
these decisions authorizes real accounts, DC access, external assets or publication.
