# Observe original rich photo receivers for late completion

Type: feature
Status: ready-for-agent
Work state: claimed
Blocked by: none for source work; coordinator owns native verification

Own this ticket and new `clients/android/patches/0023-rich-photo-observation.patch` only.
Coordinator owns series/README, shared docs, Python probes, source preparation, builds and guests.
Keep changes inside the existing GPL GramLabPhotoObserver. Do not change original rendering,
storage cleanup, image loading, input handlers, or expose a public targeting API.

Preserve schema-1 ordinary-photo activation/results exactly. Add private schema-2 activation with
exact fields schema, nonce, world_id, user_id, peer_id and targets. Targets is an ordered list of
one to eight distinct objects with exactly message_id, kind and asset_ids: positive native int32
message_id, kind ordinary or rich, and one to eight unique positive signed-int64 asset IDs. Allow
at most one target per message for this bounded seam. Match exactly one observed original Photo.id
to the explicit allowed set and report that single actual ID. Schema-2
results retain existing envelope fields and ordered messages; each message adds kind and asset_id.
Ordinary results preserve progress/icon fields; rich results use null for both because original
rich radial state has no public getter. Never infer a rich progress icon from geometry or HTTP.

Use original public ChatMessageCell/MessageObject/RichMessageLayout/RichPhotoBlock/ImageReceiver
state after draw. For rich content, require a unique direct root RichPhotoBlock with matching
original Photo.id. Preserve existing unavailable conditions and refuse animated, ambiguous,
unsupported nested/grouped, clipped or transformed geometry. Use original cell text origin and
block padding/current draw offset to project exact receiver bounds. The rich control rectangle
is the original centered 48dp input region, checked against the visible image and cell viewport.
Report original receiver key and hasImageLoaded; no reflection or synthetic receiver. Match the
pinned original draw/touch implementation independently and document exact fields/coordinates.

This extends an existing opt-in diagnostic seam under the approved media testing design. Its
native consumer still needs fresh identity/generation/age/current-process checks and screenshot
before ordinary input. It does not authorize input atomically or provide revision-bound targets.

The stronger late-edit fixture keeps a first rich photo unchanged while replacing a second rich
photo shared with an ordinary message. Original MessageObject.findPhoto returns the first photo,
so source inspection predicts MessagesStorage does not globally cancel the second old photo.
Only native evidence can prove the old transfer completes without rebinding the edited receiver.
Keep the already observed ordinary edit cleanup and shared cancel UI behavior documented.

Read licensing/upstream and parallel-work. Use normal21 source as read-only reference; no APK or
guest. Produce an append-only zero-fuzz patch, verify reconstructed source exactly, review schema-1
compatibility and strict malformed activation rejection. Keep the ticket claimed until coordinator
native guards, rich receiver geometry and unchanged ordinary regressions pass. Send frozen clean
commit, mappings, focused source evidence and remaining runtime risks.

## Worker evidence

Patch 0023 adds the strict schema-2 target parser and leaves schema-1 message-ID parsing and
ordinary observation fields on their existing path. Schema 2 accepts one to eight ordered,
message-unique targets with bounded to eight allowed asset IDs each and rejects wrong fields, kinds,
scalar types, duplicates and identifier ranges. Its ordinary target validates the original media
Photo ID is in that set before adding `kind` and the single actual `asset_id`.

The rich path accepts only an ungrouped, non-spoiler article with one matching direct-root
`RichPhotoBlock`. It reads that block's public original `photo`, `padding`, `currY` and
`imageReceiver`, rejects duplicate matches, layout animation, receiver fade/animation and ancestor
transforms, and projects receiver bounds from the cell's stable animated top padding plus original
text origin. The centered 48dp control rectangle reconstructs the original integer sizing and is
required to fit the original receiver, visible cell rectangle and complete cell. Rich progress/icon
are JSON null.
No reflection, input, storage, loader or renderer code is changed.

The patch applies to the retained normal21 source with `--fuzz=0`; the reconstructed Java file is
byte-identical to the independently edited candidate. `git diff --check` passes. Per assignment,
no APK build or Android guest was run. Coordinator still must compile, exercise malformed schema-2
activations, verify fresh observer identity/generation/age, inspect rich geometry on the original
screen and rerun schema-1 ordinary regressions before resolving this ticket.
