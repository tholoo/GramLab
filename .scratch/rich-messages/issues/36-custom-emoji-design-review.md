# Review the required custom-emoji catalog and delivery boundary

The user explicitly approved all four prepared designs and then resumed the goal. This approval
supersedes the pending-consultation instructions retained below as proposal history. Proceed with
the recommended direction; freeze shared implementation contracts before parallel dispatch.

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: none; user approved all four designs on 2026-09-07

Review [the concrete proposal](../../../docs/development/custom-emoji-proposal.md) before
implementation. Preserve optional scenario-selected logical IDs, message-specific fallback text,
incoming entities, rich button labels and transparent VP9 WebM acceptance. Do not replace the
required animated workflow with TGS-only evidence or infer owner-bot runtime restrictions from
sticker administration.

The proposed World-wide trusted fixture catalog separates synthetic admission from production
entitlement, bot-scoped file identities from logical IDs, and recipient document/media access
from bot lookup. It reuses the pending photo storage/delivery direction and coordinates versioned
dependencies with mentions. These are approved designs, not verified runtime behavior. Whole-batch
native lookup errors avoid the source's partial-Vector recursion, but visible failure/callback
cleanup and recovery still require evidence before their contract is frozen.

Original fixture preparation is independent under ticket 35. After consultation, the coordinator
must freeze the shared descriptors and error rules, assign separate implementation worktrees,
and own public/native acceptance. No catalog, API method, emoji entity, original animation or
media download is claimed implemented by this design review.

The coordinator has frozen the document, media and resolver interfaces in
[the implementation contract](../../../docs/development/custom-emoji-implementation-contract.md).
Tickets 57/58 split decoder and GPL adapter work; registration/API/entity integration follows the
same neutral schema. The approval is already recorded; further implementation work requires no
repeat design approval. This ticket remains claimed until the full catalog acceptance is proven.

## Resolver failure findings for implementation freeze

A read-only review of the pinned Android resolver confirms that a non-Vector response stops
recursive requests but retains `loadingDocuments`; another request for the same ID merely adds a
callback and cannot issue a new lookup. Successful document processing is the existing callback
removal path. An unresolved drawable has no receiver and paints nothing; preserving semantic
fallback text does not prove that Android redraws that text or displays a failure glyph.

Do not invoke arbitrary ReceivedDocument callbacks with null: StickerSetCell dereferences the
Document, and MessageObject's null branch leaves its loading flag set. The bounded candidate is
an offline-only non-Vector branch on the existing UI-thread callback that removes only the failed
batch's pending entries and clears their callback lists without invocation. Do not synthesize
Documents, return partial/empty successful vectors, or clear unrelated queues/caches. This is a
proposed failure-cleanup seam for the approved local resolver; it is not implemented or verified.

That removal allows a fresh explicit resolver lookup, but does not make an existing cached
AnimatedEmojiDrawable retry. Freeze cold restart as the first guaranteed UI recovery path unless
an additional explicit live-retry contract is established. Native acceptance must prove bounded
unknown/ungranted/mixed-batch failure, no partial metadata/storage/asset request, released pending
callbacks, a new explicit lookup and successful original decoding after restored fixture access
and cold restart. Do not claim universal visible fallback or live recovery from source inspection.

Pinned source anchors under the GPL tree: AnimatedEmojiDrawable fetchDocument (193–233),
loadFromServer (309–329), successful processDocuments (363–382), cached make (94–130),
initDocument (584–605), draw (811–834), updateAttachState (906–935); StickerSetCell (380–383),
MessageObject (4074–4084), AnimatedEmojiSpan (348–365, 493–508). Runtime's existing allowlist and
ownership-checked completion remain the transport boundary. No source, build or guest was changed
by this read-only review. Next freeze the neutral catalog/asset/lookup schemas and decoder limits
before assigning independent core/API, GPL document/delivery and real-bot acceptance branches.
