# Observe original rich photo receivers for late completion

Type: feature
Status: ready-for-agent
Work state: open
Blocked by: none for source work; coordinator owns native verification

Own this ticket and new `clients/android/patches/0023-rich-photo-observation.patch` only.
Coordinator owns series/README, shared docs, Python probes, source preparation, builds and guests.
Keep changes inside the existing GPL GramLabPhotoObserver. Do not change original rendering,
storage cleanup, image loading, input handlers, or expose a public targeting API.

Preserve schema-1 ordinary-photo activation/results exactly. Add private schema-2 activation with
exact fields schema, nonce, world_id, user_id, peer_id and targets. Targets is an ordered list of
one to eight distinct objects with exactly message_id, kind and asset_id: positive native int32
message_id, kind ordinary or rich, positive signed-int64 asset_id. Allow at most one target per
message for this bounded seam. Match observed original Photo.id to the explicit asset ID. Schema-2
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
